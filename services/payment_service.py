"""
Payment Service - Razorpay Integration
Handles order creation and payment signature verification.
NEVER exposes the secret key to the frontend.
NEVER stores card numbers, CVV, PINs, or bank credentials.
"""
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    import razorpay
    HAS_RAZORPAY = True
except ImportError:
    HAS_RAZORPAY = False
    logger.warning("razorpay package not installed — payment features disabled.")


def get_razorpay_client(key_id: str, key_secret: str):
    """Initialize Razorpay client safely."""
    if not HAS_RAZORPAY:
        return None
    if not key_id or not key_secret:
        return None
    try:
        return razorpay.Client(auth=(key_id, key_secret))
    except Exception as e:
        logger.error(f"Razorpay client init failed: {e}")
        return None


def create_order(key_id: str, key_secret: str, amount_paise: int,
                 currency: str = 'INR', receipt: str = None,
                 notes: dict = None) -> dict:
    """
    Create a Razorpay order.
    
    Returns:
        dict with 'success', 'order_id', 'amount', 'currency', 'error'
    """
    client = get_razorpay_client(key_id, key_secret)
    if not client:
        return {
            'success': False,
            'error': 'payment_not_configured',
            'message': 'Payment gateway is not configured yet. Please try again later.',
        }

    try:
        order_data = {
            'amount': amount_paise,
            'currency': currency,
            'payment_capture': 1,  # Auto-capture
        }
        if receipt:
            order_data['receipt'] = receipt
        if notes:
            order_data['notes'] = notes

        order = client.order.create(order_data)
        return {
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'receipt': order.get('receipt'),
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        return {
            'success': False,
            'error': 'order_creation_failed',
            'message': f'Failed to create payment order. Please try again. ({str(e)[:100]})',
        }


def verify_payment_signature(key_secret: str, razorpay_order_id: str,
                              razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verify Razorpay payment signature using HMAC-SHA256.
    This is the critical security step to confirm payment authenticity.
    
    Returns True if signature is valid, False otherwise.
    """
    if not key_secret or not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    try:
        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_sig = hmac.new(
            key_secret.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, razorpay_signature)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


def verify_webhook_signature(key_secret: str, webhook_body: bytes,
                              webhook_signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    if not key_secret or not webhook_body or not webhook_signature:
        return False
    try:
        expected = hmac.new(
            key_secret.encode('utf-8'),
            webhook_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, webhook_signature)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return False


def fetch_payment_details(key_id: str, key_secret: str, payment_id: str) -> dict:
    """Fetch payment details from Razorpay (for webhook verification)."""
    client = get_razorpay_client(key_id, key_secret)
    if not client:
        return {}
    try:
        return client.payment.fetch(payment_id)
    except Exception as e:
        logger.error(f"Failed to fetch payment {payment_id}: {e}")
        return {}
