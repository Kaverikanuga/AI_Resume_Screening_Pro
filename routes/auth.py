"""
Authentication Routes
Handles registration, login, logout, password reset.
"""
from datetime import datetime, timezone, timedelta
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, PasswordReset, UserSubscription
from forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from utils import rate_limit, is_safe_redirect_url
from services.email_service import send_password_reset_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if existing_user:
            flash('Email is already registered. Please log in.', 'danger')
            return render_template('auth/register.html', form=form)

        if not rate_limit('register', 10, 300):
            flash('Too many registration attempts. Please try again in a few minutes.', 'warning')
            return render_template('auth/register.html', form=form)

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # get user.id

        # Assign free subscription by default
        sub = UserSubscription(
            user_id=user.id,
            plan='free',
            status='active',
            started_at=datetime.now(timezone.utc)
        )
        db.session.add(sub)
        db.session.commit()

        login_user(user)
        flash('Account created successfully! Welcome to AI Resume Screening Pro.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        if not rate_limit('login', 15, 300):
            flash('Too many login attempts. Please wait a few minutes and try again.', 'warning')
            return render_template('auth/login.html', form=form)

        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)

            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.name}!', 'success')

            # Open-redirect guard: only follow same-host relative/absolute targets
            next_page = request.args.get('next') or request.form.get('next')
            if next_page and not is_safe_redirect_url(next_page):
                next_page = None
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        if not rate_limit('forgot_password', 5, 600):
            flash('Too many password reset requests. Please try again later.', 'warning')
            return render_template('auth/forgot_password.html', form=form)

        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            # Invalidate any previous unused tokens for this user
            PasswordReset.query.filter_by(user_id=user.id, used=False).update({'used': True})

            reset_req = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_req)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            sent = send_password_reset_email(user, reset_url)
            if sent:
                flash('If an account exists with that email, a password reset link has been sent.', 'info')
            else:
                # Development fallback when SMTP credentials are not configured
                flash(f'Password reset link generated! For development, click here: {reset_url}', 'info')
        else:
            flash('If an account exists with that email, a password reset link has been generated.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    reset_req = PasswordReset.query.filter_by(token=token).first()
    if not reset_req or not reset_req.is_valid():
        flash('Invalid or expired reset token. Please request a new link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(reset_req.user_id)
        if user:
            user.set_password(form.password.data)
            reset_req.used = True
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)
