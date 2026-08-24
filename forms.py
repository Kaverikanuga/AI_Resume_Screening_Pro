from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (StringField, PasswordField, EmailField, TextAreaField,
                     SelectField, BooleanField, HiddenField, TelField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                 Optional, Regexp)


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required.'),
        Length(min=2, max=150, message='Name must be 2–150 characters.')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=8, message='Password must be at least 8 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords do not match.')
    ])


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    remember = BooleanField('Remember me')


class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.')
    ])


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=8, message='Password must be at least 8 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords do not match.')
    ])


class ResumeUploadForm(FlaskForm):
    resume = FileField('Upload Resume (PDF)', validators=[
        FileRequired(message='Please select a PDF file.'),
        FileAllowed(['pdf'], message='Only PDF files are allowed.')
    ])


class JobMatchForm(FlaskForm):
    job_title = StringField('Job Title', validators=[
        DataRequired(message='Job title is required.'),
        Length(max=200)
    ])
    company = StringField('Company', validators=[
        Optional(),
        Length(max=200)
    ])
    job_description = TextAreaField('Job Description', validators=[
        DataRequired(message='Job description is required.'),
        Length(min=50, message='Please provide a more detailed job description (min 50 chars).')
    ])
    resume_id = HiddenField('Resume ID')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=150)
    ])
    phone = TelField('Phone', validators=[Optional(), Length(max=20)])
    location = StringField('Location', validators=[Optional(), Length(max=150)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        Length(min=8, message='Password must be at least 8 characters.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm new password.'),
        EqualTo('new_password', message='Passwords do not match.')
    ])


class CareerAssistantForm(FlaskForm):
    target_role = StringField('Target Job Role', validators=[
        DataRequired(message='Target role is required.'),
        Length(max=200)
    ])
    resume_id = HiddenField('Resume ID')


class ResumeBuilderForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = TelField('Phone', validators=[Optional(), Length(max=20)])
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    linkedin = StringField('LinkedIn URL', validators=[Optional(), Length(max=300)])
    github = StringField('GitHub URL', validators=[Optional(), Length(max=300)])
    summary = TextAreaField('Professional Summary', validators=[Optional()])
    skills = TextAreaField('Skills (comma separated)', validators=[Optional()])
    template = SelectField('Template', choices=[
        ('modern', 'Modern'),
        ('professional', 'Professional'),
        ('minimal', 'Minimal'),
        ('ats', 'ATS-Friendly'),
    ], validators=[DataRequired()])


class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=120, message='Name must be 2–120 characters.')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.')
    ])
    subject = StringField('Subject', validators=[
        Optional(),
        Length(max=200, message='Subject must be under 200 characters.')
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Message is required.'),
        Length(min=10, max=2000, message='Message must be between 10 and 2000 characters.')
    ])
