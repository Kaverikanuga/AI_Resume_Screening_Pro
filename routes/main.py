"""
Main Routes
Handles Landing page, Dashboard, Profile, Settings, History, Pricing, Contact.
"""
import hmac
import os
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user, login_user
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import (
    AdminBootstrapClaim, Resume, JobMatch, UserSubscription, Payment,
    ContactMessage,
)
from forms import ProfileForm, ChangePasswordForm, ContactForm
from services.rejection_analyzer import analyze_rejection

main_bp = Blueprint('main', __name__)
ADMIN_BOOTSTRAP_CLAIM_KEY = 'one-time'


def _canonical_email(email: str) -> str:
    """Canonicalize email address by stripping dots for Gmail/Googlemail."""
    if not email:
        return ''
    email = email.strip().lower()
    if '@' not in email:
        return email
    local_part, domain = email.split('@', 1)
    if domain in ('gmail.com', 'googlemail.com'):
        local_part = local_part.replace('.', '')
    return f"{local_part}@{domain}"


def _is_allowlisted_admin_email(email):
    if not email:
        return False
    user_canon = _canonical_email(email)
    raw_env_emails = os.environ.get('ADMIN_EMAILS', '')
    super_admin_email = os.environ.get('SUPER_ADMIN_EMAIL', 'kanugukaveri31@gmail.com')

    allowlist_entries = [entry for entry in raw_env_emails.split(',') if entry.strip()]
    if super_admin_email:
        allowlist_entries.append(super_admin_email)

    allowlisted_canons = {_canonical_email(entry) for entry in allowlist_entries if entry.strip()}
    return user_canon in allowlisted_canons


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('pages/index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    resumes = (
        Resume.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(Resume.upload_date.desc(), Resume.id.desc())
        .all()
    )
    latest_resume = resumes[0] if resumes else None

    recent_job_matches = (
        JobMatch.query.filter_by(user_id=current_user.id)
        .order_by(JobMatch.created_at.desc(), JobMatch.id.desc())
        .limit(5)
        .all()
    )

    # Job match / rejection for the latest resume only — never mix another resume's match
    latest_job_match = None
    if latest_resume:
        latest_job_match = (
            JobMatch.query.filter_by(user_id=current_user.id, resume_id=latest_resume.id)
            .order_by(JobMatch.created_at.desc(), JobMatch.id.desc())
            .first()
        )

    # Dashboard Statistics
    total_resumes = len(resumes)
    avg_ats = round(sum(r.ats_score or 0 for r in resumes) / total_resumes, 1) if total_resumes > 0 else 0
    all_job_matches = JobMatch.query.filter_by(user_id=current_user.id).all()
    total_job_matches = len(all_job_matches)
    avg_job_match = (
        round(sum(m.match_percentage or 0 for m in all_job_matches) / total_job_matches, 1)
        if total_job_matches > 0 else 0
    )

    latest_ats_data = latest_resume.get_analysis_data() if latest_resume else {}
    latest_extracted = latest_resume.get_extracted_data() if latest_resume else {}

    latest_rejection = None
    if latest_job_match and latest_resume and latest_job_match.resume_id == latest_resume.id:
        match_data = latest_job_match.get_match_data() or {}
        match_data['job_description_lower'] = (latest_job_match.job_description or '').lower()
        latest_rejection = analyze_rejection(
            extracted=latest_extracted,
            raw_text=latest_resume.raw_text or '',
            ats_scores=latest_ats_data,
            match_data=match_data
        )

    return render_template(
        'pages/dashboard.html',
        resumes=resumes,
        latest_resume=latest_resume,
        recent_job_matches=recent_job_matches,
        latest_job_match=latest_job_match,
        latest_rejection=latest_rejection,
        total_resumes=total_resumes,
        avg_ats=avg_ats,
        total_job_matches=total_job_matches,
        avg_job_match=avg_job_match,
        latest_ats_data=latest_ats_data,
        latest_extracted=latest_extracted,
        plan='admin' if current_user.check_is_admin() else current_user.get_plan()
    )


@main_bp.route('/history')
@login_required
def history():
    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.upload_date.desc()).all()
    matches = JobMatch.query.filter_by(user_id=current_user.id).order_by(JobMatch.created_at.desc()).all()
    return render_template('pages/history.html', resumes=resumes, matches=matches)


@main_bp.route('/pricing')
def pricing():
    user_plan = current_user.get_plan() if current_user.is_authenticated else 'free'
    return render_template('pages/pricing.html', current_plan=user_plan)


@main_bp.route('/admin/provision', methods=['GET', 'POST'])
@login_required
def provision_admin():
    if not _is_allowlisted_admin_email(current_user.email):
        abort(403)

    if current_user.check_is_admin():
        return render_template(
            'pages/admin_provision.html',
            message='This account already has administrator access.',
            show_form=False,
        ), 409

    claim = db.session.get(AdminBootstrapClaim, ADMIN_BOOTSTRAP_CLAIM_KEY)
    if claim:
        if claim.user_id == current_user.id:
            current_user.is_admin = True
            current_user.role = 'admin'
            db.session.commit()
            login_user(current_user, fresh=True)
            flash('Administrator access has been enabled for your account.', 'success')
            return redirect(url_for('main.dashboard'))
        return render_template(
            'pages/admin_provision.html',
            message='One-time administrator provisioning has already been completed.',
            show_form=False,
        ), 409

    if request.method == 'GET':
        return render_template(
            'pages/admin_provision.html',
            message=None,
            show_form=True,
        )

    expected_token = os.environ.get('ADMIN_BOOTSTRAP_TOKEN', '').strip()
    if len(expected_token) < 32:
        return render_template(
            'pages/admin_provision.html',
            message='Administrator setup is currently unavailable.',
            show_form=False,
        ), 503

    supplied_token = (request.form.get('bootstrap_token') or '').strip()
    if not supplied_token or not hmac.compare_digest(
        supplied_token.encode('utf-8'),
        expected_token.encode('utf-8'),
    ):
        return render_template(
            'pages/admin_provision.html',
            message='The provisioning request could not be verified.',
            show_form=True,
        ), 403

    db.session.add(AdminBootstrapClaim(
        key=ADMIN_BOOTSTRAP_CLAIM_KEY,
        user_id=current_user.id,
        claimed_at=datetime.now(timezone.utc),
    ))
    current_user.is_admin = True
    current_user.role = 'admin'
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template(
            'pages/admin_provision.html',
            message='One-time administrator provisioning has already been completed.',
            show_form=False,
        ), 409

    login_user(current_user, fresh=True)
    flash('Administrator access has been enabled for your account.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        current_user.location = form.location.data.strip() if form.location.data else None
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))
    return render_template('pages/profile.html', form=form)


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            subject=(form.subject.data or '').strip() or None,
            message=form.message.data.strip(),
        )
        db.session.add(msg)
        db.session.commit()
        flash('Thanks for reaching out! Your message has been received and our team will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('pages/contact.html', form=form)


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('main.settings'))
            
    subscription = UserSubscription.query.filter_by(user_id=current_user.id).first()
    recent_payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()

    return render_template(
        'pages/settings.html',
        form=form,
        subscription=subscription,
        payments=recent_payments,
        can_provision_admin=(
            not current_user.check_is_admin()
            and _is_allowlisted_admin_email(current_user.email)
            and db.session.get(
                AdminBootstrapClaim, ADMIN_BOOTSTRAP_CLAIM_KEY
            ) is None
        ),
    )
