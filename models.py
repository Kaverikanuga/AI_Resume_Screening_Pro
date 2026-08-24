from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Index
from extensions import db, login_manager
import json


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    avatar = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    resumes = db.relationship('Resume', backref='owner', lazy='dynamic',
                              cascade='all, delete-orphan')
    subscription = db.relationship('UserSubscription', backref='user',
                                   uselist=False, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan')
    password_resets = db.relationship('PasswordReset', backref='user', lazy='dynamic',
                                      cascade='all, delete-orphan')
    job_matches = db.relationship('JobMatch', backref='user', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_plan(self):
        if self.subscription and self.subscription.is_active():
            return self.subscription.plan
        return 'free'

    def is_pro(self):
        plan = self.get_plan()
        return plan in ('pro', 'business')

    def is_business(self):
        return self.get_plan() == 'business'

    def latest_resume(self):
        """Most recently uploaded active resume for this user."""
        return (
            Resume.query.filter_by(user_id=self.id, is_active=True)
            .order_by(Resume.upload_date.desc(), Resume.id.desc())
            .first()
        )

    def __repr__(self):
        return f'<User {self.email}>'


class Resume(db.Model):
    __tablename__ = 'resumes'
    __table_args__ = (
        Index('ix_resumes_user_active', 'user_id', 'is_active'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    # Extracted data stored as JSON
    extracted_data = db.Column(db.Text, nullable=True)  # JSON
    raw_text = db.Column(db.Text, nullable=True)

    # Analysis results
    ats_score = db.Column(db.Float, nullable=True)
    keyword_score = db.Column(db.Float, nullable=True)
    formatting_score = db.Column(db.Float, nullable=True)
    grammar_score = db.Column(db.Float, nullable=True)
    readability_score = db.Column(db.Float, nullable=True)
    analysis_data = db.Column(db.Text, nullable=True)  # JSON

    # Relationships
    job_matches = db.relationship('JobMatch', backref='resume', lazy='dynamic',
                                  cascade='all, delete-orphan')
    linkedin_reports = db.relationship('LinkedInReport', backref='resume', lazy='dynamic',
                                       cascade='all, delete-orphan')
    naukri_reports = db.relationship('NaukriReport', backref='resume', lazy='dynamic',
                                     cascade='all, delete-orphan')
    career_suggestions = db.relationship('CareerSuggestion', backref='resume', lazy='dynamic',
                                         cascade='all, delete-orphan')

    def get_extracted_data(self):
        if self.extracted_data:
            try:
                return json.loads(self.extracted_data)
            except Exception:
                return {}
        return {}

    def set_extracted_data(self, data):
        self.extracted_data = json.dumps(data)

    def get_analysis_data(self):
        if self.analysis_data:
            try:
                return json.loads(self.analysis_data)
            except Exception:
                return {}
        return {}

    def set_analysis_data(self, data):
        self.analysis_data = json.dumps(data)

    def __repr__(self):
        return f'<Resume {self.original_filename}>'


class JobMatch(db.Model):
    __tablename__ = 'job_matches'
    __table_args__ = (
        Index('ix_job_matches_user', 'user_id'),
        Index('ix_job_matches_resume', 'resume_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=True)
    company = db.Column(db.String(200), nullable=True)
    job_description = db.Column(db.Text, nullable=False)
    match_percentage = db.Column(db.Float, nullable=True)
    match_data = db.Column(db.Text, nullable=True)  # JSON
    decision = db.Column(db.String(50), nullable=True)  # RECOMMENDED / NOT_RECOMMENDED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_match_data(self):
        if self.match_data:
            try:
                return json.loads(self.match_data)
            except Exception:
                return {}
        return {}

    def set_match_data(self, data):
        self.match_data = json.dumps(data)


class LinkedInReport(db.Model):
    __tablename__ = 'linkedin_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    report_data = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_report_data(self):
        if self.report_data:
            try:
                return json.loads(self.report_data)
            except Exception:
                return {}
        return {}

    def set_report_data(self, data):
        self.report_data = json.dumps(data)


class NaukriReport(db.Model):
    __tablename__ = 'naukri_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    report_data = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_report_data(self):
        if self.report_data:
            try:
                return json.loads(self.report_data)
            except Exception:
                return {}
        return {}

    def set_report_data(self, data):
        self.report_data = json.dumps(data)


class CareerSuggestion(db.Model):
    __tablename__ = 'career_suggestions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    target_role = db.Column(db.String(200), nullable=True)
    suggestion_data = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_suggestion_data(self):
        if self.suggestion_data:
            try:
                return json.loads(self.suggestion_data)
            except Exception:
                return {}
        return {}

    def set_suggestion_data(self, data):
        self.suggestion_data = json.dumps(data)


class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    plan = db.Column(db.String(50), nullable=False, default='free')  # free/pro/business
    status = db.Column(db.String(50), nullable=False, default='active')  # active/expired/cancelled
    started_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def is_active(self):
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    def __repr__(self):
        return f'<Subscription user={self.user_id} plan={self.plan}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # in paise
    currency = db.Column(db.String(10), default='INR')
    razorpay_order_id = db.Column(db.String(200), unique=True, nullable=True)
    razorpay_payment_id = db.Column(db.String(200), nullable=True)
    razorpay_signature = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), default='pending')  # pending/success/failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Payment {self.razorpay_order_id} status={self.status}>'


class PasswordReset(db.Model):
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(300), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def is_valid(self):
        return not self.used and self.expires_at > datetime.now(timezone.utc)


class ResumeDoc(db.Model):
    """A user-created resume document managed by the Resume Editor."""
    __tablename__ = 'resume_docs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, default='My Resume')
    template = db.Column(db.String(50), nullable=False, default='modern')
    data = db.Column(db.Text, nullable=True)  # JSON blob with all resume sections
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def get_data(self):
        if self.data:
            try:
                return json.loads(self.data)
            except Exception:
                return {}
        return {}

    def set_data(self, data):
        self.data = json.dumps(data)

    def __repr__(self):
        return f'<ResumeDoc {self.title} user={self.user_id}>'


class GeneratedReport(db.Model):
    """History of downloadable PDF reports generated by the platform."""
    __tablename__ = 'generated_reports'

    KIND_LABELS = {
        'analysis': 'Resume Analysis',
        'rejection': 'AI Rejection Analysis',
        'resume_doc': 'Resume Builder Export',
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)
    kind = db.Column(db.String(50), nullable=False, default='analysis')
    filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def kind_label(self):
        return self.KIND_LABELS.get(self.kind, self.kind.replace('_', ' ').title())

    def __repr__(self):
        return f'<GeneratedReport {self.kind} {self.filename}>'


class ContactMessage(db.Model):
    """Messages submitted through the public Contact page."""
    __tablename__ = 'contact_messages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    handled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ContactMessage {self.email}>'
