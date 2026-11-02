"""
AI Resume Screening Pro - Flask Application Factory
"""
import os
import logging
import hmac
from datetime import datetime, timezone

from flask import Flask, render_template, jsonify, request
from sqlalchemy import text

from config import config_map
from extensions import db, login_manager, csrf, mail

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
        if config_name not in config_map:
            config_name = 'default'

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])
    if config_name == 'production':
        _validate_production_configuration(app.config)

    # Ensure required directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('REPORTS_FOLDER', 'reports'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.scanner import scanner_bp
    from routes.payment import payment_bp
    from routes.api import api_bp
    from routes.editor import editor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(editor_bp)

    # Create database tables + lightweight performance indexes (idempotent)
    with app.app_context():
        import models  # noqa - ensure models are registered
        db.create_all()
        _ensure_performance_indexes(app)
        logger.info("Database tables created/verified.")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"500 error: {e}")
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, url_for
        flash('File too large. Maximum allowed size is 10 MB.', 'danger')
        return redirect(url_for('scanner.upload')), 413

    # Basic security response headers (no external dependencies)
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response

    # Template globals available to every template
    @app.context_processor
    def inject_template_globals():
        return {'now': lambda: datetime.now(timezone.utc)}

    # CLI commands for secure administrator management
    _register_admin_cli_commands(app)

    logger.info(f"App created with config: {config_name}")
    return app


def _register_admin_cli_commands(app: Flask) -> None:
    """Register CLI commands to manage administrators securely via terminal."""
    import click
    from sqlalchemy.exc import IntegrityError

    def authorize_admin_operation() -> None:
        expected_token = os.environ.get('ADMIN_BOOTSTRAP_TOKEN', '')
        if len(expected_token) < 32:
            raise click.ClickException(
                'Set ADMIN_BOOTSTRAP_TOKEN to a random secret of at least 32 characters.'
            )
        provided_token = click.prompt(
            'Admin authorization token',
            hide_input=True,
        )
        if not hmac.compare_digest(
            provided_token.encode('utf-8'),
            expected_token.encode('utf-8'),
        ):
            raise click.ClickException('Admin authorization failed.')

    def require_allowlisted_email(email: str) -> str:
        email_clean = email.strip().casefold()
        configured_admin_emails = {
            entry.strip().casefold()
            for entry in os.environ.get('ADMIN_EMAILS', '').split(',')
            if entry.strip()
        }
        if email_clean not in configured_admin_emails:
            raise click.ClickException(
                'The email must be listed in the server-side ADMIN_EMAILS setting.'
            )
        return email_clean

    def prompt_admin_password() -> str:
        password = click.prompt(
            'Admin password',
            hide_input=True,
            confirmation_prompt=True,
        )
        if len(password) < 8:
            raise click.ClickException('Password must be at least 8 characters.')
        return password

    @app.cli.command('bootstrap-admin')
    @click.argument('email')
    @click.argument('name')
    def bootstrap_admin(email: str, name: str):
        """Create or securely claim an admin account using owner credentials."""
        authorize_admin_operation()
        email_clean = require_allowlisted_email(email)

        name_clean = name.strip()
        if not name_clean or len(name_clean) > 150:
            raise click.ClickException('Name must contain 1 to 150 characters.')
        password = prompt_admin_password()

        with app.app_context():
            from models import User, UserSubscription

            user = User.query.filter(
                db.func.lower(User.email) == email_clean
            ).first()
            if user is None:
                user = User(name=name_clean, email=email_clean)
                db.session.add(user)
            user.name = name_clean
            user.set_password(password)
            user.is_active = True
            user.is_admin = True
            user.role = 'admin'
            try:
                db.session.flush()
                if user.subscription is None:
                    db.session.add(UserSubscription(
                        user_id=user.id,
                        plan='free',
                        status='active',
                        started_at=datetime.now(timezone.utc),
                    ))
                db.session.commit()
            except IntegrityError as exc:
                db.session.rollback()
                raise click.ClickException(
                    'The administrator account could not be provisioned.'
                ) from exc

            click.echo(
                f"Success: Configured administrator '{email_clean}' provisioned "
                f"(User ID: {user.id})."
            )

    @app.cli.command('grant-admin')
    @click.argument('email')
    def grant_admin(email: str):
        """Grant admin using the owner token and reset the account password."""
        authorize_admin_operation()
        email_clean = require_allowlisted_email(email)
        password = prompt_admin_password()
        with app.app_context():
            from models import User
            user = User.query.filter(
                db.func.lower(User.email) == email_clean
            ).first()
            if not user:
                raise click.ClickException(
                    'No account exists for this address; use bootstrap-admin instead.'
                )
            user.set_password(password)
            user.is_active = True
            user.is_admin = True
            user.role = 'admin'
            db.session.commit()
            click.echo(f"Success: Administrator privileges granted to '{email_clean}' (User ID: {user.id}).")

    @app.cli.command('revoke-admin')
    @click.argument('email')
    def revoke_admin(email: str):
        """Revoke administrator privileges using the owner authorization token."""
        authorize_admin_operation()
        email_clean = email.strip().lower()
        with app.app_context():
            from models import User
            user = User.query.filter_by(email=email_clean).first()
            if not user:
                click.echo(f"Error: User with email '{email_clean}' not found in the database.")
                return
            user.is_admin = False
            user.role = 'user'
            db.session.commit()
            click.echo(f"Success: Administrator privileges revoked from '{email_clean}'.")


def _validate_production_configuration(app_config) -> None:
    secret_key = app_config.get('SECRET_KEY')
    if not isinstance(secret_key, str) or len(secret_key) < 32:
        raise RuntimeError(
            'Production requires a private SECRET_KEY containing at least 32 characters.'
        )

    database_uri = app_config.get('SQLALCHEMY_DATABASE_URI')
    if not isinstance(database_uri, str) or not database_uri.lower().startswith(
        ('postgresql://', 'postgresql+')
    ):
        raise RuntimeError(
            'Production requires DATABASE_URL to reference a persistent PostgreSQL database.'
        )


def _ensure_performance_indexes(app: Flask) -> None:
    """Create hot-path indexes and ensure schema columns if they do not already exist (safe to re-run)."""
    try:
        with app.app_context():
            is_postgres = db.engine.dialect.name == 'postgresql'
            bool_default = 'FALSE' if is_postgres else '0'
            statements = [
                "ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'",
                f"ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT {bool_default}",
                "CREATE INDEX IF NOT EXISTS ix_resumes_user_active ON resumes (user_id, is_active)",
                "CREATE INDEX IF NOT EXISTS ix_job_matches_user ON job_matches (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_job_matches_resume ON job_matches (resume_id)",
                "CREATE INDEX IF NOT EXISTS ix_generated_reports_user ON generated_reports (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_resume_docs_user ON resume_docs (user_id)",
            ]
            for stmt in statements:
                try:
                    db.session.execute(text(stmt))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
    except Exception as e:
        logger.warning(f"Performance index/schema verification skipped: {e}")


if __name__ == '__main__':
    application = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    application.run(host='127.0.0.1', port=port, debug=debug)
