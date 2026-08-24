"""
Scanner & Analysis Routes
Handles resume upload, parsing, ATS analysis, Job Matching, Rejection Analyzer,
Resume Builder, Resume Editor, LinkedIn, Naukri, Career Assistant, Reports Hub.
"""
import os
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, send_file, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    Resume, JobMatch, LinkedInReport, NaukriReport, CareerSuggestion, GeneratedReport
)
from forms import (
    ResumeUploadForm, JobMatchForm, CareerAssistantForm, ResumeBuilderForm
)
from utils import require_plan, can_upload_resume, can_run_job_match

from services.resume_parser import parse_resume
from services.ats_analyzer import calculate_ats_score, enrich_ats_display
from services.job_matcher import match_resume_to_job
from services.rejection_analyzer import analyze_rejection, build_resume_rejection_view
from services.linkedin_service import generate_linkedin_report
from services.naukri_service import generate_naukri_report
from services.career_service import generate_career_suggestions
from services.report_service import generate_analysis_report, generate_rejection_report

scanner_bp = Blueprint('scanner', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@scanner_bp.route('/scanner', methods=['GET', 'POST'])
@login_required
def upload():
    form = ResumeUploadForm()
    if form.validate_on_submit():
        # Backend Free Plan Quota Check
        allowed, err_msg = can_upload_resume(current_user)
        if not allowed:
            flash(err_msg, 'warning')
            return render_template('pages/premium_lock.html', required_plan='pro')

        file = form.resume.data
        if file and allowed_file(file.filename):
            orig_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{orig_filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            file_size = os.path.getsize(file_path)

            try:
                # 1. Parse Resume
                extracted = parse_resume(file_path)
                raw_text = (extracted.get('raw_text') or '').strip()
                if not raw_text:
                    raise ValueError(
                        'Could not extract any text from this PDF. '
                        'The file may be image-based, scanned, or corrupted. No analysis was generated.'
                    )

                # 2. Calculate ATS Score from this file only
                ats_result = calculate_ats_score(extracted, raw_text)

                # 3. Save Resume in DB
                resume = Resume(
                    user_id=current_user.id,
                    filename=unique_filename,
                    original_filename=orig_filename,
                    file_path=file_path,
                    file_size=file_size,
                    raw_text=raw_text,
                    ats_score=ats_result.get('overall_score'),
                    keyword_score=ats_result.get('keyword_score'),
                    formatting_score=ats_result.get('formatting_score'),
                    grammar_score=ats_result.get('grammar_score'),
                    readability_score=ats_result.get('readability_score'),
                )
                resume.set_extracted_data(extracted)
                resume.set_analysis_data(ats_result)

                db.session.add(resume)
                db.session.commit()

                flash('Resume scanned successfully!', 'success')
                return redirect(url_for('scanner.analysis', resume_id=resume.id))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing resume: {e}", exc_info=True)
                flash(
                    f'PDF parsing failed: {str(e)} No fake analysis was generated. '
                    'Please upload a text-based PDF resume.',
                    'danger'
                )
                return render_template('scanner/upload.html', form=form)

    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.upload_date.desc()).all()
    return render_template('scanner/upload.html', form=form, resumes=resumes)


@scanner_bp.route('/analysis/<int:resume_id>')
@login_required
def analysis(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    extracted = resume.get_extracted_data() or {}
    ats_data = enrich_ats_display(extracted, resume.raw_text or '', resume.get_analysis_data() or {})

    # Job match and rejection must belong to THIS resume only
    job_match = (
        JobMatch.query.filter_by(resume_id=resume.id)
        .order_by(JobMatch.created_at.desc(), JobMatch.id.desc())
        .first()
    )
    match_data = None
    if job_match:
        match_data = job_match.get_match_data() or {}
        match_data['job_title'] = job_match.job_title or match_data.get('job_title', '')
        match_data['company'] = job_match.company or match_data.get('company', '')
        match_data['job_description_lower'] = (job_match.job_description or '').lower()
        if 'decision' not in match_data and job_match.decision:
            match_data['decision'] = job_match.decision
        if match_data.get('overall_match') is None and job_match.match_percentage is not None:
            match_data['overall_match'] = job_match.match_percentage

    rejection = build_resume_rejection_view(
        extracted=extracted,
        raw_text=resume.raw_text or '',
        ats_scores=ats_data,
        match_data=match_data
    )

    return render_template(
        'scanner/analysis.html',
        resume=resume,
        extracted=extracted,
        ats_data=ats_data,
        latest_job_match=job_match,
        rejection=rejection
    )



@scanner_bp.route('/job-match', methods=['GET', 'POST'])
@scanner_bp.route('/job-match/<int:resume_id>', methods=['GET', 'POST'])
@login_required
def job_match(resume_id=None):
    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.upload_date.desc()).all()
    if not resumes:
        flash('Please upload a resume first before running Job Match.', 'warning')
        return redirect(url_for('scanner.upload'))

    selected_resume = None
    if resume_id:
        selected_resume = Resume.query.get_or_404(resume_id)
        if selected_resume.user_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('scanner.job_match'))
    else:
        selected_resume = resumes[0]

    form = JobMatchForm()
    if request.method == 'GET' and selected_resume:
        form.resume_id.data = str(selected_resume.id)

    if form.validate_on_submit():
        # Backend Free Plan Quota Check for Job Match
        allowed, err_msg = can_run_job_match(current_user)
        if not allowed:
            flash(err_msg, 'warning')
            return render_template('pages/premium_lock.html', required_plan='pro')

        target_resume_id = int(form.resume_id.data) if form.resume_id.data else selected_resume.id
        target_resume = Resume.query.get_or_404(target_resume_id)

        if target_resume.user_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('scanner.job_match'))

        extracted = target_resume.get_extracted_data()
        raw_text = target_resume.raw_text or ''
        jd_text = form.job_description.data.strip()
        job_title = form.job_title.data.strip()
        company = form.company.data.strip() if form.company.data else ''

        # Match resume to job
        match_result = match_resume_to_job(
            extracted=extracted,
            raw_text=raw_text,
            jd_text=jd_text,
            job_title=job_title,
            company=company
        )

        # Save JobMatch record
        match_record = JobMatch(
            user_id=current_user.id,
            resume_id=target_resume.id,
            job_title=job_title,
            company=company,
            job_description=jd_text,
            match_percentage=match_result.get('overall_match'),
            decision=match_result.get('decision')
        )
        match_record.set_match_data(match_result)
        db.session.add(match_record)
        db.session.commit()

        flash('Job Match analysis completed!', 'success')
        return redirect(url_for('scanner.job_match_result', job_match_id=match_record.id))

    recent_matches = JobMatch.query.filter_by(user_id=current_user.id).order_by(JobMatch.created_at.desc()).limit(10).all()

    return render_template(
        'scanner/job_match_form.html',
        form=form,
        resumes=resumes,
        selected_resume=selected_resume,
        recent_matches=recent_matches
    )


@scanner_bp.route('/resume/<int:resume_id>/delete', methods=['POST'])
@login_required
def delete_resume(resume_id):
    """Soft-delete an uploaded resume (frees free-plan quota slots)."""
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    resume.is_active = False
    db.session.commit()
    flash(f'Resume "{resume.original_filename}" removed from your account.', 'info')
    return redirect(request.referrer or url_for('main.history'))


@scanner_bp.route('/job-match/result/<int:job_match_id>')
@login_required
def job_match_result(job_match_id):
    match_record = JobMatch.query.get_or_404(job_match_id)
    if match_record.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    match_data = match_record.get_match_data()
    resume = match_record.resume

    return render_template(
        'scanner/job_match_result.html',
        match_record=match_record,
        match_data=match_data,
        resume=resume
    )


@scanner_bp.route('/rejection-analysis/<int:job_match_id>')
@login_required
@require_plan('pro')
def rejection_analysis(job_match_id):
    match_record = JobMatch.query.get_or_404(job_match_id)
    if match_record.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    resume = match_record.resume
    extracted = resume.get_extracted_data()
    raw_text = resume.raw_text or ''
    ats_scores = resume.get_analysis_data()
    match_data = match_record.get_match_data() or {}
    match_data['job_description_lower'] = (match_record.job_description or '').lower()
    match_data['job_title'] = match_record.job_title or match_data.get('job_title', '')

    rejection_result = analyze_rejection(
        extracted=extracted,
        raw_text=raw_text,
        ats_scores=ats_scores,
        match_data=match_data
    )

    return render_template(
        'scanner/rejection_analysis.html',
        match_record=match_record,
        resume=resume,
        rejection=rejection_result,
        ats_data=ats_scores
    )


@scanner_bp.route('/linkedin/<int:resume_id>')
@login_required
@require_plan('pro')
def linkedin(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    extracted = resume.get_extracted_data()
    ats_scores = resume.get_analysis_data()

    report_record = LinkedInReport.query.filter_by(resume_id=resume.id).order_by(LinkedInReport.created_at.desc()).first()
    if not report_record:
        report_data = generate_linkedin_report(extracted, ats_scores)
        report_record = LinkedInReport(
            user_id=current_user.id,
            resume_id=resume.id
        )
        report_record.set_report_data(report_data)
        db.session.add(report_record)
        db.session.commit()
    else:
        report_data = report_record.get_report_data()

    return render_template(
        'scanner/linkedin.html',
        resume=resume,
        report=report_data
    )


@scanner_bp.route('/naukri/<int:resume_id>')
@login_required
@require_plan('pro')
def naukri(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    extracted = resume.get_extracted_data()
    ats_scores = resume.get_analysis_data()

    report_record = NaukriReport.query.filter_by(resume_id=resume.id).order_by(NaukriReport.created_at.desc()).first()
    if not report_record:
        report_data = generate_naukri_report(extracted, ats_scores)
        report_record = NaukriReport(
            user_id=current_user.id,
            resume_id=resume.id
        )
        report_record.set_report_data(report_data)
        db.session.add(report_record)
        db.session.commit()
    else:
        report_data = report_record.get_report_data()

    return render_template(
        'scanner/naukri.html',
        resume=resume,
        report=report_data
    )


@scanner_bp.route('/career/<int:resume_id>', methods=['GET', 'POST'])
@login_required
@require_plan('pro')
def career(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    extracted = resume.get_extracted_data()
    form = CareerAssistantForm()

    if request.method == 'GET':
        default_role = extracted.get('skills', {}).get('technical', ['Software Developer'])[0] if extracted.get('skills', {}).get('technical') else 'Software Developer'
        form.target_role.data = default_role

    career_data = None
    if form.validate_on_submit():
        target_role = form.target_role.data.strip()
        career_data = generate_career_suggestions(extracted, target_role)
        
        sug_record = CareerSuggestion(
            user_id=current_user.id,
            resume_id=resume.id,
            target_role=target_role
        )
        sug_record.set_suggestion_data(career_data)
        db.session.add(sug_record)
        db.session.commit()
    else:
        last_sug = CareerSuggestion.query.filter_by(resume_id=resume.id).order_by(CareerSuggestion.created_at.desc()).first()
        if last_sug:
            career_data = last_sug.get_suggestion_data()
            # Keep the visible form in sync with the roadmap actually being displayed
            if career_data.get('target_role'):
                form.target_role.data = career_data['target_role']
        else:
            target_role = form.target_role.data or 'Software Developer'
            career_data = generate_career_suggestions(extracted, target_role)

    return render_template(
        'scanner/career.html',
        form=form,
        resume=resume,
        career=career_data
    )


@scanner_bp.route('/resume-builder', methods=['GET', 'POST'])
@login_required
@require_plan('pro')
def resume_builder():
    form = ResumeBuilderForm()
    if request.method == 'GET':
        form.full_name.data = current_user.name
        form.email.data = current_user.email
        form.phone.data = current_user.phone or ''
        form.location.data = current_user.location or ''

    if form.validate_on_submit():
        builder_data = {
            'full_name': form.full_name.data,
            'email': form.email.data,
            'phone': form.phone.data,
            'location': form.location.data,
            'linkedin': form.linkedin.data,
            'github': form.github.data,
            'summary': form.summary.data,
            'skills': [s.strip() for s in form.skills.data.split(',') if s.strip()] if form.skills.data else [],
            'template': form.template.data
        }
        return render_template('scanner/resume_builder_preview.html', data=builder_data)

    return render_template('scanner/resume_builder.html', form=form)


@scanner_bp.route('/resume-editor/<int:resume_id>', methods=['GET', 'POST'])
@login_required
def resume_editor(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    extracted = resume.get_extracted_data()
    # Guarantee the skills structure exists even on legacy/partial records
    extracted.setdefault('skills', {})
    extracted['skills'].setdefault('technical', [])
    extracted['skills'].setdefault('soft', [])

    if request.method == 'POST':
        # Validate & clamp incoming fields before persisting anything
        def _field(key, fallback, max_len):
            value = (request.form.get(key) or '').strip()[:max_len]
            return value or fallback

        extracted['name'] = _field('name', extracted.get('name', ''), 150)
        email_value = _field('email', extracted.get('email', ''), 150)
        if email_value and '@' not in email_value:
            flash('Please enter a valid email address.', 'danger')
            return render_template('scanner/resume_editor.html', resume=resume, extracted=extracted), 400
        extracted['email'] = email_value
        extracted['phone'] = _field('phone', extracted.get('phone', ''), 25)
        extracted['location'] = _field('location', extracted.get('location', ''), 150)
        extracted['summary'] = _field('summary', extracted.get('summary', ''), 1500)

        tech_skills_raw = request.form.get('technical_skills', '')
        extracted['skills']['technical'] = [s.strip()[:40] for s in tech_skills_raw.split(',') if s.strip()][:60]

        soft_skills_raw = request.form.get('soft_skills', '')
        extracted['skills']['soft'] = [s.strip()[:40] for s in soft_skills_raw.split(',') if s.strip()][:40]

        # Re-score using the ORIGINAL document text plus any corrected contact/summary/skills,
        # so word counts and keyword coverage stay meaningful after an edit.
        original_text = resume.raw_text or ''
        corrected_bits = " ".join(
            part for part in [
                extracted.get('name', ''),
                extracted.get('summary', ''),
                " ".join(extracted['skills']['technical']),
            ] if part
        )
        raw_text = f"{original_text} {corrected_bits}".strip()
        ats_result = calculate_ats_score(extracted, raw_text)

        try:
            resume.set_extracted_data(extracted)
            resume.set_analysis_data(ats_result)
            resume.ats_score = ats_result.get('overall_score')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Resume editor save failed: {e}", exc_info=True)
            flash('Could not save your changes right now. Please try again.', 'danger')
            return render_template('scanner/resume_editor.html', resume=resume, extracted=extracted)

        flash('Resume updated and re-analyzed successfully!', 'success')
        return redirect(url_for('scanner.analysis', resume_id=resume.id))

    return render_template('scanner/resume_editor.html', resume=resume, extracted=extracted)


@scanner_bp.route('/reports')
@login_required
def reports_hub():
    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.upload_date.desc()).all()
    recent_reports = (
        GeneratedReport.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedReport.created_at.desc(), GeneratedReport.id.desc())
        .limit(20)
        .all()
    )
    return render_template('pages/reports.html', resumes=resumes, recent_reports=recent_reports)


@scanner_bp.route('/reports/<int:report_id>/file')
@login_required
def download_stored_report(report_id):
    """Re-download a previously generated report file."""
    record = GeneratedReport.query.get_or_404(report_id)
    if record.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('scanner.reports_hub'))

    if not os.path.exists(record.file_path):
        flash('This report file is no longer available on disk. Generate a fresh copy instead.', 'warning')
        return redirect(url_for('scanner.reports_hub'))

    return send_file(record.file_path, as_attachment=True, download_name=record.filename)


@scanner_bp.route('/reports/<int:resume_id>/download')
@login_required
@require_plan('pro')
def download_report(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    report_filename = f"report_{resume.id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join(current_app.config['REPORTS_FOLDER'], report_filename)

    extracted = resume.get_extracted_data()
    ats_data = resume.get_analysis_data()

    last_match = JobMatch.query.filter_by(resume_id=resume.id).order_by(JobMatch.created_at.desc()).first()
    match_data = last_match.get_match_data() if last_match else {}

    rejection_data = {}
    if last_match and last_match.decision != 'RECOMMENDED':
        rejection_data = analyze_rejection(extracted, resume.raw_text or '', ats_data, match_data)

    success = generate_analysis_report(
        resume_data=extracted,
        ats_data=ats_data,
        match_data=match_data,
        rejection_data=rejection_data,
        output_path=output_path,
        user_name=current_user.name
    )

    if not success or not os.path.exists(output_path):
        flash('Could not generate PDF report.', 'danger')
        return redirect(url_for('scanner.analysis', resume_id=resume.id))

    try:
        db.session.add(GeneratedReport(
            user_id=current_user.id,
            resume_id=resume.id,
            kind='analysis',
            filename=report_filename,
            file_path=output_path,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return send_file(output_path, as_attachment=True, download_name=f"Resume_Report_{current_user.name.replace(' ', '_')}.pdf")


@scanner_bp.route('/rejection-analysis/<int:job_match_id>/download')
@login_required
@require_plan('pro')
def download_rejection_report(job_match_id):
    """Dedicated AI Rejection Analyzer PDF report."""
    match_record = JobMatch.query.get_or_404(job_match_id)
    if match_record.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    resume = match_record.resume
    extracted = resume.get_extracted_data()
    ats_scores = resume.get_analysis_data()
    match_data = match_record.get_match_data() or {}
    match_data['job_description_lower'] = (match_record.job_description or '').lower()
    match_data['job_title'] = match_record.job_title or match_data.get('job_title', '')

    rejection_result = analyze_rejection(
        extracted=extracted,
        raw_text=resume.raw_text or '',
        ats_scores=ats_scores,
        match_data=match_data
    )

    report_filename = f"rejection_{match_record.id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join(current_app.config['REPORTS_FOLDER'], report_filename)

    success = generate_rejection_report(
        job_title=match_record.job_title or 'Target Role',
        company=match_record.company or '',
        candidate_name=extracted.get('name') or current_user.name,
        ats_data=ats_scores,
        match_data=match_data,
        rejection_data=rejection_result,
        output_path=output_path,
    )

    if not success or not os.path.exists(output_path):
        flash('Could not generate the rejection analysis PDF.', 'danger')
        return redirect(url_for('scanner.rejection_analysis', job_match_id=match_record.id))

    try:
        db.session.add(GeneratedReport(
            user_id=current_user.id,
            resume_id=resume.id,
            kind='rejection',
            filename=report_filename,
            file_path=output_path,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return send_file(output_path, as_attachment=True, download_name=f"Rejection_Analysis_{match_record.id}.pdf")
