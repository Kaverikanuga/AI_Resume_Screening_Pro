"""
Report Service - ReportLab PDF Generation
Generates professional PDF reports for resume analysis.
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("reportlab not installed — PDF reports disabled.")


def generate_analysis_report(resume_data: dict, ats_data: dict,
                              match_data: dict, rejection_data: dict,
                              output_path: str, user_name: str = '') -> bool:
    """
    Generate a comprehensive PDF analysis report.
    Returns True on success, False on failure.
    """
    if not HAS_REPORTLAB:
        logger.error("ReportLab not available — cannot generate PDF report.")
        return False

    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=22,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=10,
            alignment=TA_CENTER,
        )
        heading1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#0077b6'),
            spaceBefore=14,
            spaceAfter=6,
        )
        heading2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#023e8a'),
            spaceBefore=10,
            spaceAfter=4,
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4,
        )
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
        )

        story = []
        now = datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')

        # ── Cover Header ─────────────────────────────────────────────────
        story.append(Paragraph('AI Resume Screening Pro', title_style))
        story.append(Paragraph('Comprehensive Resume Analysis Report', 
                               ParagraphStyle('sub', parent=styles['Normal'],
                                              fontSize=12, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#555555'))))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f'Generated: {now}', 
                               ParagraphStyle('date', parent=styles['Normal'],
                                              fontSize=9, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#888888'))))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0077b6')))
        story.append(Spacer(1, 10))

        # ── Candidate Information ─────────────────────────────────────────
        story.append(Paragraph('Candidate Information', heading1_style))
        
        candidate_info = [
            ['Field', 'Value'],
            ['Name', resume_data.get('name', 'Not detected') or 'Not detected'],
            ['Email', resume_data.get('email', 'Not detected') or 'Not detected'],
            ['Phone', resume_data.get('phone', 'Not detected') or 'Not detected'],
            ['Location', resume_data.get('location', 'Not detected') or 'Not detected'],
            ['LinkedIn', resume_data.get('linkedin', 'Not provided') or 'Not provided'],
        ]
        
        t = Table(candidate_info, colWidths=[3*cm, 13*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f7ff')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f7ff'), colors.white]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccddee')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

        # ── ATS Score Summary ─────────────────────────────────────────────
        story.append(Paragraph('ATS Score Analysis', heading1_style))
        
        overall = ats_data.get('overall_score', 0)
        score_color = colors.HexColor(
            '#22c55e' if overall >= 75 else
            '#f59e0b' if overall >= 50 else
            '#ef4444'
        )
        
        score_data = [
            ['Metric', 'Score', 'Rating'],
            ['Overall ATS Score', f'{overall:.1f}/100', _rating_label(overall)],
            ['Keyword Score', f'{ats_data.get("keyword_score", 0):.1f}/100', _rating_label(ats_data.get("keyword_score", 0))],
            ['Formatting Score', f'{ats_data.get("formatting_score", 0):.1f}/100', _rating_label(ats_data.get("formatting_score", 0))],
            ['Skills Score', f'{ats_data.get("skills_score", 0):.1f}/100', _rating_label(ats_data.get("skills_score", 0))],
            ['Education Score', f'{ats_data.get("education_score", 0):.1f}/100', _rating_label(ats_data.get("education_score", 0))],
            ['Experience Score', f'{ats_data.get("experience_score", 0):.1f}/100', _rating_label(ats_data.get("experience_score", 0))],
        ]
        
        t = Table(score_data, colWidths=[7*cm, 5*cm, 4*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#023e8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f4f8'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbccdd')),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

        # ── Strengths ─────────────────────────────────────────────────────
        story.append(Paragraph('Resume Strengths', heading1_style))
        strengths = ats_data.get('strengths', [])
        if strengths:
            for s in strengths:
                story.append(Paragraph(f'• {s}', normal_style))
        else:
            story.append(Paragraph('No specific strengths identified.', normal_style))

        story.append(Spacer(1, 8))

        # ── Weaknesses ────────────────────────────────────────────────────
        story.append(Paragraph('Areas for Improvement', heading1_style))
        weaknesses = ats_data.get('weaknesses', [])
        if weaknesses:
            for w in weaknesses:
                story.append(Paragraph(f'⚠ {w}', normal_style))
        else:
            story.append(Paragraph('No major weaknesses identified.', normal_style))

        story.append(Spacer(1, 8))

        # ── Job Match (if available) ───────────────────────────────────────
        if match_data and match_data.get('overall_match') is not None:
            story.append(Paragraph('Job Match Analysis', heading1_style))

            match_info = [
                ['Metric', 'Value'],
                ['Overall Match', f'{match_data.get("overall_match", 0):.1f}%'],
                ['Skill Match', f'{match_data.get("skill_match_pct", 0):.1f}%'],
                ['Keyword Match', f'{match_data.get("keyword_match_pct", 0):.1f}%'],
                ['Application Decision', match_data.get("decision_label", "N/A")],
            ]

            t = Table(match_info, colWidths=[7*cm, 9*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f4f8'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbccdd')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t)

            # Missing skills
            missing = match_data.get('missing_skills', [])
            if missing:
                story.append(Spacer(1, 6))
                story.append(Paragraph('Missing Skills', heading2_style))
                story.append(Paragraph(', '.join(missing[:12]), normal_style))

        # ── Rejection Analysis (if available) ─────────────────────────────
        if rejection_data and rejection_data.get('critical_reasons'):
            story.append(PageBreak())
            story.append(Paragraph('AI Screening-Based Rejection Analysis', heading1_style))
            story.append(Paragraph(
                'DISCLAIMER: This section reflects AI screening analysis only. '
                'It does NOT represent actual reasons from any company.',
                ParagraphStyle('disclaimer', parent=styles['Normal'],
                               fontSize=8, textColor=colors.HexColor('#888888'),
                               backColor=colors.HexColor('#fff3cd'),
                               borderPadding=5)
            ))
            story.append(Spacer(1, 8))

            story.append(Paragraph(f'Estimated Match Score: {rejection_data.get("match_percentage", 0):.1f}%', heading2_style))
            story.append(Paragraph(f'Estimated Improved Score: {rejection_data.get("estimated_improved_match", 0):.1f}%', heading2_style))

            story.append(Paragraph('Critical Issues', heading2_style))
            for reason in rejection_data.get('critical_reasons', []):
                story.append(Paragraph(f'❌ {reason["title"]}: {reason["description"]}', normal_style))

            story.append(Paragraph('Improvement Recommendations', heading2_style))
            for imp in rejection_data.get('improvements', []):
                story.append(Paragraph(f'✓ {imp}', normal_style))

        # ── Skills ────────────────────────────────────────────────────────
        story.append(Spacer(1, 10))
        story.append(Paragraph('Detected Skills', heading1_style))
        tech_skills = resume_data.get('skills', {}).get('technical', [])
        if tech_skills:
            story.append(Paragraph(', '.join(tech_skills[:30]), normal_style))
        else:
            story.append(Paragraph('No technical skills detected.', normal_style))

        # ── Footer ────────────────────────────────────────────────────────
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        story.append(Paragraph(
            'Generated by AI Resume Screening Pro — For guidance purposes only.',
            ParagraphStyle('footer', parent=styles['Normal'],
                           fontSize=8, textColor=colors.HexColor('#999999'),
                           alignment=TA_CENTER)
        ))

        doc.build(story)
        return True

    except Exception as e:
        logger.error(f"PDF report generation failed: {e}", exc_info=True)
        return False


REJECTION_DISCLAIMER = (
    "This analysis is AI-generated guidance and does not represent an actual "
    "employer hiring decision."
)


def _rating_label(score: float) -> str:
    if score >= 80:
        return 'Excellent'
    elif score >= 65:
        return 'Good'
    elif score >= 50:
        return 'Average'
    elif score >= 35:
        return 'Below Average'
    else:
        return 'Poor'


def _esc(text) -> str:
    """Escape XML-sensitive characters for ReportLab Paragraphs."""
    import html as _html
    return _html.escape(str(text or ''))


def generate_rejection_report(job_title: str, company: str, candidate_name: str,
                              ats_data: dict, match_data: dict,
                              rejection_data: dict, output_path: str) -> bool:
    """
    Generate a dedicated AI Rejection Analyzer PDF report.
    Returns True on success, False on failure.
    """
    if not HAS_REPORTLAB:
        logger.error("ReportLab not available - cannot generate rejection PDF.")
        return False

    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'RejTitle', parent=styles['Title'], fontSize=20,
            textColor=colors.HexColor('#1a1a2e'), spaceAfter=8, alignment=TA_CENTER)
        h1 = ParagraphStyle('RejH1', parent=styles['Heading1'], fontSize=13,
                            textColor=colors.HexColor('#0077b6'), spaceBefore=12, spaceAfter=5)
        h2 = ParagraphStyle('RejH2', parent=styles['Heading2'], fontSize=11,
                            textColor=colors.HexColor('#023e8a'), spaceBefore=8, spaceAfter=3)
        normal = ParagraphStyle('RejNormal', parent=styles['Normal'], fontSize=9.5,
                                textColor=colors.HexColor('#333333'), spaceAfter=4)
        disclaimer_style = ParagraphStyle(
            'RejDisclaimer', parent=styles['Normal'], fontSize=8.5,
            textColor=colors.HexColor('#7a5b00'), backColor=colors.HexColor('#fff3cd'),
            borderPadding=6)

        story = []
        now = datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')

        story.append(Paragraph('AI Rejection Analyzer Report', title_style))
        story.append(Paragraph(
            f"Candidate: {_esc(candidate_name)} &nbsp;|&nbsp; Job Role: {_esc(job_title)}"
            + (f" &nbsp;|&nbsp; Company: {_esc(company)}" if company else ''),
            ParagraphStyle('sub', parent=styles['Normal'], fontSize=10,
                           alignment=TA_CENTER, textColor=colors.HexColor('#555555'))))
        story.append(Paragraph(f'Generated: {now}',
                               ParagraphStyle('date', parent=styles['Normal'], fontSize=8.5,
                                              alignment=TA_CENTER, textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0077b6')))
        story.append(Spacer(1, 8))

        # Mandatory disclaimer (exact wording required by product spec)
        story.append(Paragraph(REJECTION_DISCLAIMER, disclaimer_style))
        story.append(Spacer(1, 10))

        # ── Score summary ────────────────────────────────────────────────
        overall_match = float(rejection_data.get('match_percentage') or match_data.get('overall_match') or 0)
        ats_overall = float((ats_data or {}).get('overall_score') or 0)
        risk = float(rejection_data.get('rejection_risk') or max(0, 100 - overall_match))
        potential = float(rejection_data.get('estimated_improved_match') or 0)
        delta = float(rejection_data.get('improvement_delta') or max(0, potential - overall_match))

        score_rows = [
            ['Metric', 'Value'],
            ['Screening Status', rejection_data.get('rejection_status', 'N/A')],
            ['Current Match Score', f'{overall_match:.1f}%'],
            ['ATS Score', f'{ats_overall:.1f}/100'],
            ['Rejection Risk', f'{risk:.1f}%'],
            ['Potential Match Score', f'{potential:.1f}%'],
            ['Improvement Potential', f'+{delta:.1f}%'],
            ['Skill Match', f"{float(match_data.get('skill_match_pct') or 0):.1f}%"],
            ['Keyword Match', f"{float(match_data.get('keyword_match_pct') or 0):.1f}%"],
        ]
        t = Table(score_rows, colWidths=[7*cm, 9*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#023e8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f4f8'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbccdd')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

        # ── Section scores ───────────────────────────────────────────────
        component_scores = (ats_data or {}).get('component_scores') or {}
        if component_scores:
            story.append(Paragraph('Resume Section Scores', h1))
            comp_rows = [['Section', 'Score']]
            for name, value in component_scores.items():
                comp_rows.append([str(name), f'{float(value or 0):.1f}/100'])
            t = Table(comp_rows, colWidths=[9*cm, 7*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9.5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f7ff'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccddee')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        # ── Primary reason ───────────────────────────────────────────────
        primary = rejection_data.get('primary_reason')
        if primary:
            story.append(Paragraph('Primary Screening Concern', h1))
            story.append(Paragraph(_esc(primary), normal))
            story.append(Spacer(1, 6))

        # ── Reason tiers ─────────────────────────────────────────────────
        def _reason_block(title, items):
            if not items:
                return
            story.append(Paragraph(title, h2))
            for reason in items:
                story.append(Paragraph(f"- <b>{_esc(reason.get('title', ''))}</b>: "
                                       f"{_esc(reason.get('description', ''))}", normal))

        _reason_block('Critical Issues (High Rejection Impact)', rejection_data.get('critical_reasons'))
        _reason_block('Major Issues (Moderate Rejection Risk)', rejection_data.get('major_reasons'))
        _reason_block('Minor Issues & Formatting Concerns', rejection_data.get('minor_issues'))

        # ── Gaps ─────────────────────────────────────────────────────────
        missing_skills = rejection_data.get('missing_skills') or []
        missing_keywords = rejection_data.get('missing_keywords') or []
        if missing_skills or missing_keywords:
            story.append(Paragraph('Skill & Keyword Gaps', h1))
            if missing_skills:
                story.append(Paragraph('<b>Missing required skills:</b> ' +
                                       _esc(', '.join(missing_skills)), normal))
            if missing_keywords:
                story.append(Paragraph('<b>High-frequency job keywords missing:</b> ' +
                                       _esc(', '.join(missing_keywords)), normal))
            story.append(Spacer(1, 6))

        # ── Improvements ─────────────────────────────────────────────────
        improvements = rejection_data.get('improvements') or []
        if improvements:
            story.append(Paragraph('How To Improve (Action Checklist)', h1))
            for imp in improvements:
                story.append(Paragraph(f"[ ] {_esc(imp)}", normal))

        # ── Footer ───────────────────────────────────────────────────────
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
        story.append(Paragraph(REJECTION_DISCLAIMER,
                               ParagraphStyle('foot', parent=styles['Normal'], fontSize=7.5,
                                              textColor=colors.HexColor('#999999'), alignment=TA_CENTER)))

        doc.build(story)
        return True

    except Exception as e:
        logger.error(f"Rejection PDF generation failed: {e}", exc_info=True)
        return False


def generate_resume_pdf(data: dict, output_path: str) -> bool:
    """
    Export a Resume Editor document (models.ResumeDoc JSON) to a clean,
    ATS-friendly PDF resume. Returns True on success.
    """
    if not HAS_REPORTLAB:
        logger.error("ReportLab not available - cannot export resume PDF.")
        return False

    data = data or {}

    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.8*cm,
            leftMargin=1.8*cm,
            topMargin=1.6*cm,
            bottomMargin=1.6*cm,
        )

        styles = getSampleStyleSheet()
        name_style = ParagraphStyle('RName', parent=styles['Title'], fontSize=19,
                                    textColor=colors.HexColor('#111111'), alignment=TA_CENTER,
                                    spaceAfter=2)
        contact_style = ParagraphStyle('RContact', parent=styles['Normal'], fontSize=9,
                                       textColor=colors.HexColor('#444444'), alignment=TA_CENTER,
                                       spaceAfter=2)
        section_style = ParagraphStyle('RSection', parent=styles['Heading2'], fontSize=11.5,
                                       textColor=colors.HexColor('#023e8a'), spaceBefore=10,
                                       spaceAfter=3)
        body = ParagraphStyle('RBody', parent=styles['Normal'], fontSize=9.5,
                              textColor=colors.HexColor('#222222'), spaceAfter=2)
        bullet = ParagraphStyle('RBullet', parent=body, leftIndent=14, bulletIndent=4)

        story = []

        full_name = _esc(data.get('full_name') or 'Your Name')
        story.append(Paragraph(full_name, name_style))

        contact_bits = [b for b in [
            data.get('email'), data.get('phone'), data.get('location'),
        ] if b]
        link_bits = [b for b in [data.get('linkedin'), data.get('github'), data.get('website')] if b]
        line1 = ' | '.join(contact_bits)
        line2 = ' | '.join(link_bits)
        if line1:
            story.append(Paragraph(_esc(line1), contact_style))
        if line2:
            story.append(Paragraph(_esc(line2), contact_style))
        story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#023e8a')))
        story.append(Spacer(1, 6))

        def section(title):
            story.append(Paragraph(_esc(title).upper(), section_style))
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#99bbdd')))
            story.append(Spacer(1, 3))

        summary = (data.get('summary') or '').strip()
        if summary:
            section('Professional Summary')
            story.append(Paragraph(_esc(summary), body))

        skills = data.get('skills') or []
        if skills:
            section('Skills')
            story.append(Paragraph(_esc(', '.join(skills)), body))

        experience = data.get('experience') or []
        internships = data.get('internships') or []
        if experience or internships:
            section('Professional Experience')

            def entry_block(entry):
                title_line = entry.get('title') or ''
                org = entry.get('company') or ''
                period = ' - '.join(p for p in [entry.get('start'), entry.get('end')] if p)
                loc = entry.get('location') or ''
                meta = ' | '.join(m for m in [org, loc, period] if m)
                head = f"<b>{_esc(title_line)}</b>" + (f" &mdash; {_esc(meta)}" if meta else '')
                story.append(Paragraph(head, body))
                for b in entry.get('bullets') or []:
                    story.append(Paragraph(_esc(b), bullet, bulletText='\u2022'))
                story.append(Spacer(1, 3))

            for entry in experience:
                entry_block(entry)
            for entry in internships:
                entry_block(entry)

        projects = data.get('projects') or []
        if projects:
            section('Projects')
            for proj in projects:
                head = f"<b>{_esc(proj.get('name'))}</b>"
                if proj.get('tech'):
                    head += f" <font size=8 color='#666666'>({_esc(proj.get('tech'))})</font>"
                story.append(Paragraph(head, body))
                if proj.get('description'):
                    story.append(Paragraph(_esc(proj['description']), bullet))
                if proj.get('link'):
                    story.append(Paragraph(f"Link: {_esc(proj['link'])}", bullet))
                story.append(Spacer(1, 3))

        education = data.get('education') or []
        if education:
            section('Education')
            for edu in education:
                degree = edu.get('degree') or ''
                inst = edu.get('institution') or ''
                years = ' - '.join(p for p in [edu.get('start_year'), edu.get('end_year')] if p)
                grade = edu.get('grade') or ''
                meta = ' | '.join(m for m in [inst, years, grade] if m)
                story.append(Paragraph(f"<b>{_esc(degree)}</b>" + (f" &mdash; {_esc(meta)}" if meta else ''), body))

        certifications = data.get('certifications') or []
        if certifications:
            section('Certifications')
            for cert in certifications:
                bits = ' | '.join(m for m in [cert.get('name'), cert.get('issuer'), cert.get('year')] if m)
                story.append(Paragraph(f"\u2022 {_esc(bits)}", bullet))

        achievements = data.get('achievements') or []
        if achievements:
            section('Achievements')
            for ach in achievements:
                story.append(Paragraph(f"\u2022 {_esc(ach)}", bullet))

        languages = data.get('languages') or []
        if languages:
            section('Languages')
            story.append(Paragraph(_esc(', '.join(languages)), body))

        doc.build(story)
        return True

    except Exception as e:
        logger.error(f"Resume PDF export failed: {e}", exc_info=True)
        return False
