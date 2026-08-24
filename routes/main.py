"""
Main Routes
Handles Landing page, Dashboard, Profile, Settings, History, Pricing, Contact.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Resume, JobMatch, UserSubscription, Payment, ContactMessage
from forms import ProfileForm, ChangePasswordForm, ContactForm
from services.rejection_analyzer import analyze_rejection

main_bp = Blueprint('main', __name__)


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
        plan=current_user.get_plan()
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
        payments=recent_payments
    )
