"""
Razorpay Payment Routes
Handles order creation, signature verification, subscription activation.
"""
from datetime import datetime, timezone, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    jsonify, current_app
)
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect

from extensions import db, csrf
from models import Payment, UserSubscription
from services.payment_service import (
    create_order, verify_payment_signature, verify_webhook_signature
)

payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/payment/create-order', methods=['POST'])
@login_required
def create_payment_order():
    data = request.get_json() or {}
    plan = data.get('plan')

    if plan not in current_app.config['PRICING']:
        return jsonify({
            'success': False,
            'error': 'invalid_plan',
            'message': 'Invalid subscription plan selected.'
        }), 400

    plan_info = current_app.config['PRICING'][plan]
    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')

    if not key_id or not key_secret:
        return jsonify({
            'success': False,
            'error': 'gateway_not_configured',
            'message': 'Payment gateway is not configured yet. Live checkout requires Razorpay credentials.'
        }), 503

    receipt = f"rec_{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}"
    
    order_result = create_order(
        key_id=key_id,
        key_secret=key_secret,
        amount_paise=plan_info['amount'],
        currency=plan_info['currency'],
        receipt=receipt,
        notes={'user_id': current_user.id, 'plan': plan}
    )

    if not order_result.get('success'):
        return jsonify(order_result), 400

    # Save pending Payment in DB
    payment = Payment(
        user_id=current_user.id,
        plan=plan,
        amount=plan_info['amount'],
        currency=plan_info['currency'],
        razorpay_order_id=order_result['order_id'],
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({
        'success': True,
        'order_id': order_result['order_id'],
        'amount': order_result['amount'],
        'currency': order_result['currency'],
        'key_id': key_id,
        'user_name': current_user.name,
        'user_email': current_user.email,
        'plan': plan
    })


@payment_bp.route('/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    data = request.get_json() or {}
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    plan = data.get('plan')

    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')

    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return jsonify({
            'success': False,
            'message': 'Missing payment verification details.'
        }), 400

    # Server-side HMAC signature verification
    is_valid = verify_payment_signature(
        key_secret=key_secret,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature
    )

    if not is_valid:
        payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
        if payment:
            payment.status = 'failed'
            db.session.commit()

        return jsonify({
            'success': False,
            'message': 'Invalid payment signature. Verification failed.'
        }), 400

    # Signature valid! Locate the pending Payment created at order time.
    # The plan/amount always come from OUR database row - never from client input.
    payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not payment or payment.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'Unknown payment order. Please start a new checkout.'
        }), 404

    # Idempotency: never extend an already-activated subscription on replayed calls
    if payment.status == 'success':
        return jsonify({
            'success': True,
            'message': 'Payment already verified. Subscription is active.',
            'redirect_url': url_for('payment.payment_success')
        })

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = 'success'

    _activate_subscription(payment)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Payment verified successfully! Subscription activated.',
        'redirect_url': url_for('payment.payment_success')
    })


def _activate_subscription(payment: Payment) -> None:
    """Grant/renew a 30-day subscription for the payment's owner (idempotent per payment)."""
    sub = UserSubscription.query.filter_by(user_id=payment.user_id).first()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=30)  # 30-day subscription

    if sub:
        sub.plan = payment.plan
        sub.status = 'active'
        sub.started_at = now
        sub.expires_at = expires
    else:
        sub = UserSubscription(
            user_id=payment.user_id,
            plan=payment.plan,
            status='active',
            started_at=now,
            expires_at=expires
        )
        db.session.add(sub)


@payment_bp.route('/payment/success')
@login_required
def payment_success():
    return render_template('pages/payment_success.html')


@payment_bp.route('/payment/failed')
@login_required
def payment_failed():
    return render_template('pages/payment_failed.html')


@payment_bp.route('/payment/webhook', methods=['POST'])
@csrf.exempt  # Server-to-server endpoint: Razorpay cannot send CSRF tokens.
def webhook():
    """
    Razorpay webhook receiver.

    Handles:
      - payment.captured / payment.authorized : mark success + activate subscription
      - payment.failed                        : mark failure

    Signature is verified against RAZORPAY_WEBHOOK_SECRET before any processing.
    """
    key_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET')
    signature = request.headers.get('X-Razorpay-Signature')
    body = request.get_data()

    if not verify_webhook_signature(key_secret, body, signature):
        current_app.logger.warning("Webhook rejected: invalid or missing signature.")
        return jsonify({'status': 'invalid signature'}), 400

    data = request.get_json(silent=True) or {}
    event = data.get('event')

    payload = data.get('payload', {}).get('payment', {}).get('entity', {})
    order_id = payload.get('order_id')
    payment_id = payload.get('id')

    if event in ('payment.captured', 'payment.authorized') and order_id:
        payment = Payment.query.filter_by(razorpay_order_id=order_id).first()
        if payment and payment.status != 'success':
            payment.status = 'success'
            payment.razorpay_payment_id = payment_id
            _activate_subscription(payment)   # Webhook alone can now fulfill the purchase
            try:
                db.session.commit()
                current_app.logger.info(f"Webhook fulfilled order {order_id} for user {payment.user_id}.")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Webhook fulfillment failed for {order_id}: {e}")
                return jsonify({'status': 'error'}), 500
        elif payment:
            # Already fulfilled via client-side verify - keep idempotent
            if payment_id and not payment.razorpay_payment_id:
                payment.razorpay_payment_id = payment_id
                db.session.commit()

    elif event == 'payment.failed' and order_id:
        payment = Payment.query.filter_by(razorpay_order_id=order_id).first()
        if payment and payment.status == 'pending':
            payment.status = 'failed'
            db.session.commit()

    return jsonify({'status': 'ok'}), 200
