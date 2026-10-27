"""
AI Resume Screening Pro - Flask Application Factory
"""
import os
import logging
from datetime import datetime, timezone

from flask import Flask, render_template, jsonify, request
from sqlalchemy import text
from dotenv import load_dotenv

from config import config_map
from extensions import db, login_manager, csrf, mail

# Load environment variables
load_dotenv()

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

    @app.cli.command('grant-admin')
    @click.argument('email')
    def grant_admin(email: str):
        """Securely grant administrator privileges to a registered user account."""
        email_clean = email.strip().lower()
        with app.app_context():
            from models import User
            user = User.query.filter_by(email=email_clean).first()
            if not user:
                click.echo(f"Error: User with email '{email_clean}' not found in the database.")
                click.echo("Please register the user first via the web interface (/register), then run this command.")
                return
            user.is_admin = True
            user.role = 'admin'
            db.session.commit()
            click.echo(f"Success: Administrator privileges granted to '{email_clean}' (User ID: {user.id}).")

    @app.cli.command('revoke-admin')
    @click.argument('email')
    def revoke_admin(email: str):
        """Revoke administrator privileges from a user account."""
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
