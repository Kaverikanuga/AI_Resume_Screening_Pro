"""
Resume Editor Routes
Professional multi-section resume documents with autosave, manual save,
duplicate, delete, live preview and PDF export.

Data model: models.ResumeDoc (JSON document per user).
All endpoints are login-required and ownership-checked.
"""
import os
import re
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    jsonify, current_app, send_file
)
from flask_login import login_required, current_user

from extensions import db
from models import ResumeDoc, GeneratedReport
from services.report_service import generate_resume_pdf

editor_bp = Blueprint('editor', __name__)

ALLOWED_TEMPLATES = {'modern', 'professional', 'minimal', 'ats'}

# Per-collection caps to keep documents sane and PDF generation fast
LIMITS = {
    'skills': 60,
    'education': 10,
    'experience': 15,
    'internships': 10,
    'projects': 12,
    'certifications': 15,
    'achievements': 15,
    'languages': 12,
}

ENTRY_FIELDS = {
    'education': {'degree': 150, 'institution': 150, 'start_year': 20, 'end_year': 20, 'grade': 50},
    'experience': {'title': 150, 'company': 150, 'location': 100, 'start': 30, 'end': 30},
    'internships': {'title': 150, 'company': 150, 'location': 100, 'start': 30, 'end': 30},
    'projects': {'name': 150, 'tech': 200, 'description': 700, 'link': 300},
    'certifications': {'name': 150, 'issuer': 120, 'year': 20},
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _s(value, max_len=300):
    """Sanitize a single string field."""
    if value is None:
        return ''
    return str(value).strip()[:max_len]


def _clean_str_list(items, max_items, max_len=200):
    out = []
    for item in (items or []):
        text = _s(item, max_len)
        if text:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _clean_entries(items, field_map, max_items):
    """Normalize a list of dict entries against an allowed field map."""
    cleaned = []
    for raw in (items or [])[:max_items]:
        if not isinstance(raw, dict):
            continue
        entry = {key: _s(raw.get(key), limit) for key, limit in field_map.items()}
        entry['bullets'] = _clean_str_list(raw.get('bullets'), 8, 250)
        has_content = any(entry[key] for key in field_map) or entry['bullets']
        if has_content:
            cleaned.append(entry)
    return cleaned


def normalize_doc(data: dict) -> dict:
    """Validate/clamp an incoming document payload into a safe shape."""
    data = data if isinstance(data, dict) else {}

    skills_raw = data.get('skills')
    if isinstance(skills_raw, str):
        skills_raw = skills_raw.split(',')
    skills = []
    for skill in (skills_raw or [])[:LIMITS['skills']]:
        text = _s(skill, 40)
        if text:
            skills.append(text)

    achievements = _clean_str_list(data.get('achievements'), LIMITS['achievements'], 250)
    languages = _clean_str_list(data.get('languages'), LIMITS['languages'], 40)

    template = _s(data.get('template'), 30).lower()
    if template not in ALLOWED_TEMPLATES:
        template = 'modern'

    return {
        'full_name': _s(data.get('full_name'), 150),
        'email': _s(data.get('email'), 150),
        'phone': _s(data.get('phone'), 25),
        'location': _s(data.get('location'), 150),
        'linkedin': _s(data.get('linkedin'), 300),
        'github': _s(data.get('github'), 300),
        'website': _s(data.get('website'), 300),
        'summary': _s(data.get('summary'), 1500),
        'skills': skills,
        'education': _clean_entries(data.get('education'), ENTRY_FIELDS['education'], LIMITS['education']),
        'experience': _clean_entries(data.get('experience'), ENTRY_FIELDS['experience'], LIMITS['experience']),
        'internships': _clean_entries(data.get('internships'), ENTRY_FIELDS['internships'], LIMITS['internships']),
        'projects': _clean_entries(data.get('projects'), ENTRY_FIELDS['projects'], LIMITS['projects']),
        'certifications': _clean_entries(data.get('certifications'), ENTRY_FIELDS['certifications'], LIMITS['certifications']),
        'achievements': achievements,
        'languages': languages,
        'template': template,
    }


def default_doc() -> dict:
    """Blank document pre-filled from the user's profile."""
    return {
        'full_name': current_user.name or '',
        'email': current_user.email or '',
        'phone': current_user.phone or '',
        'location': current_user.location or '',
        'linkedin': '',
        'github': '',
        'website': '',
        'summary': '',
        'skills': [],
        'education': [],
        'experience': [],
        'internships': [],
        'projects': [],
        'certifications': [],
        'achievements': [],
        'languages': [],
        'template': 'modern',
    }


def get_owned_doc_or_404(doc_id: int) -> ResumeDoc:
    doc = ResumeDoc.query.get_or_404(doc_id)
    if doc.user_id != current_user.id or not doc.is_active:
        abort_owner()
    return doc


def abort_owner():
    from flask import abort
    abort(403)


def slugify(text: str) -> str:
    text = re.sub(r'[^A-Za-z0-9]+', '_', (text or 'resume').strip())
    return text.strip('_')[:60] or 'resume'


# ── Routes ─────────────────────────────────────────────────────────────────

@editor_bp.route('/editor')
@login_required
def index():
    docs = (
        ResumeDoc.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(ResumeDoc.updated_at.desc(), ResumeDoc.id.desc())
        .all()
    )
    return render_template('scanner/editor_list.html', docs=docs)


@editor_bp.route('/editor/create', methods=['POST'])
@login_required
def create():
    title = _s(request.form.get('title'), 200) or 'My Resume'
    doc = ResumeDoc(
        user_id=current_user.id,
        title=title,
        template='modern',
    )
    doc.set_data(default_doc())
    db.session.add(doc)
    db.session.commit()
    flash('New resume created. Start editing!', 'success')
    return redirect(url_for('editor.edit', doc_id=doc.id))


@editor_bp.route('/editor/<int:doc_id>/edit')
@login_required
def edit(doc_id):
    doc = get_owned_doc_or_404(doc_id)
    return render_template(
        'scanner/editor_form.html',
        doc=doc,
        data=doc.get_data(),
        templates=sorted(ALLOWED_TEMPLATES),
    )


@editor_bp.route('/editor/<int:doc_id>/save', methods=['POST'])
@login_required
def save(doc_id):
    return _persist(doc_id)


@editor_bp.route('/editor/<int:doc_id>/autosave', methods=['POST'])
@login_required
def autosave(doc_id):
    return _persist(doc_id, autosave=True)


def _persist(doc_id, autosave=False):
    doc = get_owned_doc_or_404(doc_id)

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({'success': False, 'message': 'Invalid payload.'}), 400

    doc.title = _s(payload.get('title'), 200) or doc.title or 'My Resume'
    normalized = normalize_doc(payload.get('data') or {})
    doc.template = normalized['template']
    doc.set_data(normalized)
    doc.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Resume doc save failed: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Could not save right now.'}), 500

    stamp = doc.updated_at.strftime('%H:%M:%S')
    mode = 'Autosaved' if autosave else 'Saved'
    return jsonify({
        'success': True,
        'mode': mode.lower(),
        'updated_at': stamp,
        'message': f'{mode} at {stamp}',
    })


@editor_bp.route('/editor/<int:doc_id>/duplicate', methods=['POST'])
@login_required
def duplicate(doc_id):
    source = get_owned_doc_or_404(doc_id)
    copy = ResumeDoc(
        user_id=current_user.id,
        title=_s(source.title, 190)[:190] + ' (Copy)',
        template=source.template,
    )
    copy.set_data(source.get_data())
    db.session.add(copy)
    db.session.commit()
    flash(f'Duplicated "{source.title}".', 'success')
    return redirect(url_for('editor.index'))


@editor_bp.route('/editor/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete(doc_id):
    doc = get_owned_doc_or_404(doc_id)
    title = doc.title
    db.session.delete(doc)
    db.session.commit()
    flash(f'Deleted resume "{title}".', 'info')
    return redirect(url_for('editor.index'))


@editor_bp.route('/editor/<int:doc_id>/preview')
@login_required
def preview(doc_id):
    doc = get_owned_doc_or_404(doc_id)
    return render_template(
        'scanner/editor_preview.html',
        doc=doc,
        data=doc.get_data(),
    )


@editor_bp.route('/editor/<int:doc_id>/export-pdf')
@login_required
def export_pdf(doc_id):
    doc = get_owned_doc_or_404(doc_id)
    data = doc.get_data()

    report_filename = f"resume_{doc.id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join(current_app.config['REPORTS_FOLDER'], report_filename)

    success = generate_resume_pdf(data, output_path)
    if not success or not os.path.exists(output_path):
        flash('Could not export this resume to PDF right now.', 'danger')
        return redirect(url_for('editor.edit', doc_id=doc.id))

    try:
        record = GeneratedReport(
            user_id=current_user.id,
            resume_id=None,
            kind='resume_doc',
            filename=report_filename,
            file_path=output_path,
        )
        db.session.add(record)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return send_file(
        output_path,
        as_attachment=True,
        download_name=f"{slugify(doc.title)}.pdf",
    )