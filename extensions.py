from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

try:
    from flask_mail import Mail
    mail = Mail()
except ImportError:
    class DummyMail:
        def init_app(self, app):
            pass
        def send(self, message):
            pass
    mail = DummyMail()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
