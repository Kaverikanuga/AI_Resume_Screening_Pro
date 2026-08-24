"""
Rejection Analyzer Service
Provides AI screening-based rejection reasons when a resume doesn't match a job.
All values are computed dynamically — nothing is hardcoded.

IMPORTANT DISCLAIMER:
This tool provides AI screening-based analysis of resume vs. job description.
It does NOT claim to know the actual reasons a real company rejected a candidate.
Labels: "AI Screening-Based Rejection Reasons" or 
        "Likely Rejection Reasons Based on Resume and Job Description"
"""
import re
import logging
import math

logger = logging.getLogger(__name__)


def analyze_rejection(extracted: dict, raw_text: str, ats_scores: dict, match_data: dict) -> dict:
    """
    Comprehensive rejection analysis.
    Returns structured data including decision, reasons, improvements, and
    an estimated improved match score.

    Parameters:
        extracted   - parsed resume data
        raw_text    - raw resume text
        ats_scores  - results from ats_analyzer
        match_data  - results from job_matcher

    Returns dict with all rejection analysis data.
    """
    match_percentage = match_data.get('overall_match', 0)
    decision = match_data.get('decision', 'NOT_RECOMMENDED')

    critical_reasons = []
    major_reasons = []
    minor_issues = []

    missing_skills = match_data.get('missing_skills', [])
    matching_skills = match_data.get('matching_skills', [])
    skill_match_pct = match_data.get('skill_match_pct', 0)
    keyword_match_pct = match_data.get('keyword_match_pct', 0)
    role_analysis = match_data.get('role_analysis', {})
    edu_match = match_data.get('education_match', {})
    exp_match = match_data.get('experience_match', {})
    project_score = match_data.get('project_score', 0)
    cert_score = match_data.get('cert_score', 0)
    ats_overall = ats_scores.get('overall_score', 0)

    # ── CRITICAL REASONS (deal-breakers) ────────────────────────────────

    # 1. Missing required skills
    if len(missing_skills) >= 5:
        critical_reasons.append({
            'icon': '❌',
            'title': 'Critical Skills Gap',
            'description': f'Your resume is missing {len(missing_skills)} skills required by this job, '
                           f'including: {", ".join(missing_skills[:5])}. '
                           f'These are likely core requirements for this role.'
        })
    elif len(missing_skills) >= 2:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Missing Key Skills',
            'description': f'Resume is missing {len(missing_skills)} relevant skills: '
                           f'{", ".join(missing_skills[:4])}.'
        })

    # 2. Low job-description keyword match
    if keyword_match_pct < 25:
        critical_reasons.append({
            'icon': '❌',
            'title': 'Very Low Keyword Alignment',
            'description': f'Only {keyword_match_pct:.0f}% of job description keywords appear in your resume. '
                           f'ATS systems prioritize keyword-matched resumes. '
                           f'Missing keywords: {", ".join(match_data.get("jd_keywords", [])[:5])}.'
        })
    elif keyword_match_pct < 45:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Low Keyword Match',
            'description': f'Keyword alignment is {keyword_match_pct:.0f}% — below the recommended 50%+. '
                           f'Incorporate more job-specific terms into your resume.'
        })

    # 3. Low skill match percentage
    if skill_match_pct < 30:
        critical_reasons.append({
            'icon': '❌',
            'title': 'Insufficient Skill Match',
            'description': f'Only {skill_match_pct:.0f}% of your skills match the job requirements. '
                           f'This is significantly below the recommended 50%+ threshold.'
        })

    # 4. Role/domain mismatch
    if not role_analysis.get('role_matched', True):
        jd_domain = role_analysis.get('jd_domain', 'the required field')
        if match_percentage < 40:
            critical_reasons.append({
                'icon': '❌',
                'title': 'Job Role Mismatch',
                'description': f'Your resume does not demonstrate sufficient alignment with '
                               f'{jd_domain} domain requirements. Consider adding relevant '
                               f'projects, skills, or certifications in this area.'
            })
        else:
            major_reasons.append({
                'icon': '⚠',
                'title': 'Partial Role Alignment',
                'description': f'Your background partially matches {jd_domain} requirements '
                               f'but needs stronger domain-specific evidence.'
            })

    # 5. Education mismatch
    edu_score = edu_match.get('score', 70)
    if edu_score < 40:
        critical_reasons.append({
            'icon': '❌',
            'title': 'Education Requirement Not Met',
            'description': 'The job description may require a specific degree or qualification '
                           'that was not clearly found in your resume. Ensure your education '
                           'section is clearly formatted with degree, institution, and year.'
        })
    elif edu_score < 60:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Education Partially Matches',
            'description': 'Your education may not fully satisfy the stated requirements. '
                           + (edu_match.get('issues', [''])[0] if edu_match.get('issues') else '')
        })

    # 6. Experience mismatch
    exp_score = exp_match.get('score', 60)
    if exp_score < 35:
        critical_reasons.append({
            'icon': '❌',
            'title': 'Experience Requirement Not Met',
            'description': f'This role likely requires work experience that is not clearly '
                           f'demonstrated in your resume. '
                           + (exp_match.get('issues', [''])[0] if exp_match.get('issues') else '')
        })
    elif exp_score < 55:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Insufficient Experience Evidence',
            'description': 'The experience level shown in your resume may not meet the job '
                           'requirements. Add internships, projects, or freelance work.'
        })

    # ── MAJOR REASONS ────────────────────────────────────────────────────

    # 7. Weak professional summary
    summary_score = ats_scores.get('summary_score', 50)
    if summary_score < 40:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Weak or Missing Professional Summary',
            'description': 'A professional summary is the first thing ATS and recruiters see. '
                           'A missing or weak summary reduces your chances of passing initial screening. '
                           'Write a 3–5 sentence summary highlighting your key strengths and target role.'
        })

    # 8. Missing projects
    if project_score < 40:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Insufficient Project Evidence',
            'description': 'No relevant projects were found. Projects demonstrate practical skills '
                           'and are especially important for freshers and junior roles. '
                           'Add 2–3 projects with clear descriptions and tech stacks.'
        })

    # 9. Missing certifications
    certs = extracted.get('certifications', [])
    if not certs and 'certif' in match_data.get('job_description_lower', ''):
        major_reasons.append({
            'icon': '⚠',
            'title': 'No Certifications Listed',
            'description': 'This job may value certifications. Consider adding relevant courses '
                           'or certifications (AWS, Google, Coursera, NPTEL, etc.).'
        })

    # 10. Low ATS score
    if ats_overall < 40:
        major_reasons.append({
            'icon': '⚠',
            'title': 'Low Overall ATS Score',
            'description': f'Your resume ATS score is {ats_overall:.0f}/100. Many companies use ATS '
                           f'to filter resumes automatically. A low score means your resume may be '
                           f'filtered out before a human reads it.'
        })

    # ── MINOR ISSUES ─────────────────────────────────────────────────────

    # 11. Formatting
    formatting_score = ats_scores.get('formatting_score', 70)
    if formatting_score < 60:
        minor_issues.append({
            'icon': '⚠',
            'title': 'Formatting Improvements Needed',
            'description': 'Formatting issues can confuse ATS parsers. Use standard sections, '
                           'avoid tables/graphics, and ensure all key sections are clearly labeled.'
        })

    # 12. Missing measurable achievements
    measurable = extracted.get('measurable_achievements_count', 0)
    if measurable < 2:
        minor_issues.append({
            'icon': '⚠',
            'title': 'Few Measurable Achievements',
            'description': 'Quantifying achievements (e.g., "Increased performance by 35%", '
                           '"Led a team of 5") makes your resume significantly more impactful.'
        })

    # 13. Action verbs
    action_verbs = ats_scores.get('action_verbs', [])
    if len(action_verbs) < 4:
        minor_issues.append({
            'icon': '⚠',
            'title': 'Weak Action Verbs',
            'description': 'Use strong action verbs to begin each bullet point: '
                           '"Developed", "Implemented", "Achieved", "Led", "Optimized".'
        })

    # 14. Missing contact info
    if not extracted.get('linkedin'):
        minor_issues.append({
            'icon': '⚠',
            'title': 'No LinkedIn Profile',
            'description': 'Adding a LinkedIn profile URL increases recruiter trust and visibility.'
        })

    # ── PRIMARY REASON ───────────────────────────────────────────────────

    if critical_reasons:
        primary_reason = critical_reasons[0]['description']
    elif major_reasons:
        primary_reason = (
            f'Your resume matches {match_percentage:.0f}% of this job description. '
            + major_reasons[0]['description']
        )
    else:
        primary_reason = (
            f'While your resume shows some alignment ({match_percentage:.0f}% match), '
            f'there are several areas that could be strengthened to improve your '
            f'chances with ATS systems and recruiters.'
        )

    # ── IMPROVEMENT RECOMMENDATIONS ───────────────────────────────────────

    improvements = []
    if missing_skills:
        improvements.append(f'Add missing technical skills: {", ".join(missing_skills[:6])}.')
    if not extracted.get('summary') or summary_score < 50:
        improvements.append('Write or strengthen your professional summary (3–5 sentences).')
    if project_score < 50:
        improvements.append('Add 2–3 relevant projects with clear descriptions and tech stack used.')
    if keyword_match_pct < 50:
        improvements.append('Incorporate more keywords from the job description naturally into your resume.')
    if measurable < 3:
        improvements.append('Add measurable achievements: percentages, numbers, and impact metrics.')
    if len(action_verbs) < 5:
        improvements.append('Start every experience bullet with a strong action verb.')
    if not certs:
        improvements.append('Earn relevant certifications (AWS, Google Cloud, Coursera, NPTEL).')
    if not extracted.get('linkedin'):
        improvements.append('Add your LinkedIn and GitHub profile URLs.')
    if formatting_score < 60:
        improvements.append('Use ATS-friendly formatting: standard section headers, no tables/graphics.')

    # ── ESTIMATED IMPROVED MATCH SCORE ───────────────────────────────────

    improvement_points = 0

    # Each fixable issue adds potential points
    if missing_skills:
        # Adding missing skills could add up to ~20 points
        potential = min(20, len(missing_skills) * 2.5)
        improvement_points += potential

    if not extracted.get('summary') or summary_score < 50:
        improvement_points += 5

    if project_score < 50:
        improvement_points += 7

    if keyword_match_pct < 50:
        improvement_points += min(10, (50 - keyword_match_pct) * 0.4)

    if measurable < 3:
        improvement_points += 4

    if len(action_verbs) < 5:
        improvement_points += 3

    if not certs:
        improvement_points += 3

    if formatting_score < 60:
        improvement_points += 4

    # Apply diminishing returns to improvement
    # The lower the current score, the more room for improvement
    improvement_factor = 1.0 + (100 - match_percentage) / 100 * 0.3
    total_improvement = improvement_points * improvement_factor

    estimated_improved = round(min(95, match_percentage + total_improvement), 1)

    # Ensure it's higher than current (at least +5 if there are issues)
    if estimated_improved <= match_percentage and (critical_reasons or major_reasons):
        estimated_improved = min(95, match_percentage + 8)

    # Rejection status label
    if decision == 'RECOMMENDED':
        rejection_status = 'LIKELY TO PASS ATS SCREENING'
        rejection_status_icon = '✓'
        rejection_status_color = 'success'
    elif decision == 'CONDITIONALLY_RECOMMENDED':
        rejection_status = 'MAY PASS ATS WITH IMPROVEMENTS'
        rejection_status_icon = '⚠'
        rejection_status_color = 'warning'
    else:
        rejection_status = 'LIKELY TO BE FILTERED BY ATS'
        rejection_status_icon = '❌'
        rejection_status_color = 'danger'

    # Compute rejection score (inverse of match)
    rejection_risk = round(100 - match_percentage, 1)

    return {
        'decision': decision,
        'match_percentage': round(match_percentage, 1),
        'estimated_improved_match': estimated_improved,
        'improvement_delta': round(estimated_improved - match_percentage, 1),
        'primary_reason': primary_reason,
        'critical_reasons': critical_reasons,
        'major_reasons': major_reasons,
        'minor_issues': minor_issues,
        'missing_skills': missing_skills[:12],
        'missing_keywords': match_data.get('jd_keywords', [])[:10],
        'matching_skills': matching_skills[:12],
        'strengths': match_data.get('strengths', [])[:6],
        'improvements': improvements[:8],
        'rejection_status': rejection_status,
        'rejection_status_icon': rejection_status_icon,
        'rejection_status_color': rejection_status_color,
        'rejection_risk': rejection_risk,
        'ats_score': round(ats_overall, 1),
        'keyword_match_pct': round(keyword_match_pct, 1),
        'skill_match_pct': round(skill_match_pct, 1),
        'total_issues': len(critical_reasons) + len(major_reasons) + len(minor_issues),
        'disclaimer': (
            'DISCLAIMER: This analysis is based on AI screening of your resume against '
            'the provided job description. It does NOT represent the actual reasons any '
            'company may accept or reject your application. Use this as a guide to improve '
            'your resume.'
        ),
    }


def build_resume_rejection_view(extracted: dict, raw_text: str, ats_scores: dict,
                                match_data: dict = None) -> dict:
    """
    Resume-scoped rejection explanation for the analysis page.

    Always uses this resume's ATS data. Job-match issues are included only when
    match_data comes from a JobMatch stored for the same resume.
    Does not invent an exact future ATS score.
    """
    extracted = extracted or {}
    ats_scores = ats_scores or {}
    has_job_match = bool(match_data) and 'decision' in match_data

    overall = float(ats_scores.get('overall_score') or 0)
    keyword_score = float(ats_scores.get('keyword_score') or 0)
    formatting_score = float(ats_scores.get('formatting_score') or 0)
    summary_score = float(ats_scores.get('summary_score') or 0)
    experience_score = float(ats_scores.get('experience_score') or 0)
    projects_score = float(ats_scores.get('projects_score') or 0)
    education_score = float(ats_scores.get('education_score') or 0)

    risk_percent = round(max(0, min(100, 100 - overall)), 1)
    if has_job_match:
        match_pct = float(match_data.get('overall_match') or 0)
        risk_percent = round(max(risk_percent, max(0, min(100, 100 - match_pct))), 1)

    if risk_percent >= 50:
        risk_level, risk_color = 'High', 'danger'
    elif risk_percent >= 30:
        risk_level, risk_color = 'Medium', 'warning'
    else:
        risk_level, risk_color = 'Low', 'success'

    critical_issues = []
    formatting_issues = []
    weak_sections = []
    why_parts = []

    if overall < 40:
        critical_issues.append({
            'title': 'Low overall ATS score',
            'description': f'This resume scored {overall:.0f}/100. Many ATS tools rank or filter on overall parse quality and keyword coverage.',
        })
        why_parts.append(f'the overall ATS score is {overall:.0f}/100')
    if not extracted.get('email') or not extracted.get('phone'):
        critical_issues.append({
            'title': 'Incomplete contact information',
            'description': 'ATS systems and recruiters expect a clear name, email, and phone number at the top of the resume.',
        })
        why_parts.append('contact details are incomplete')
    if keyword_score < 40:
        critical_issues.append({
            'title': 'Weak keyword coverage',
            'description': f'Keyword score is {keyword_score:.0f}/100. Resumes with few action verbs and common role terms are easier for ATS to skip.',
        })
        why_parts.append('keyword coverage is weak')

    if formatting_score < 60:
        formatting_issues.append(
            f'Formatting score is {formatting_score:.0f}/100. Use standard section headers (Education, Experience, Skills, Projects) and avoid tables or graphics.'
        )
    if not extracted.get('name'):
        formatting_issues.append('Candidate name was not clearly detected at the top of the resume.')
    if ats_scores.get('sections_missing'):
        formatting_issues.append(
            'Missing or unlabeled sections: ' + ', '.join(
                s.capitalize() for s in (ats_scores.get('sections_missing') or [])
            )
        )

    if not extracted.get('summary') or summary_score < 40:
        weak_sections.append('Professional Summary is missing or too weak for ATS and recruiter screening.')
    if not extracted.get('experience') or experience_score < 40:
        weak_sections.append('Work / internship experience is missing or not clearly structured.')
    if not extracted.get('projects') or projects_score < 40:
        weak_sections.append('Projects section is missing or does not show technologies used.')
    if not extracted.get('education') or education_score < 40:
        weak_sections.append('Education section is missing or incomplete.')
    if not (extracted.get('skills') or {}).get('technical'):
        weak_sections.append('Technical skills list was not detected.')

    job_match_issues = []
    missing_skills = []
    missing_keywords = list(ats_scores.get('missing_keywords_general') or [])
    skills_label = 'general'
    keywords_label = 'general'

    if has_job_match:
        jd_missing = match_data.get('missing_skills') or []
        if jd_missing:
            missing_skills = list(jd_missing)
            skills_label = 'job'
        jd_keywords = match_data.get('jd_keywords') or []
        resume_words = set((raw_text or '').lower().split())
        jd_missing_kw = [kw for kw in jd_keywords if kw.lower() not in resume_words]
        if jd_missing_kw:
            missing_keywords = jd_missing_kw[:12]
            keywords_label = 'job'

        if match_data.get('decision') == 'NOT_RECOMMENDED':
            job_match_issues.append(
                f"This resume is not recommended for the analyzed job "
                f"({match_data.get('job_title') or 'target role'}) at "
                f"{float(match_data.get('overall_match') or 0):.0f}% match."
            )
        elif match_data.get('decision') == 'CONDITIONALLY_RECOMMENDED':
            job_match_issues.append(
                f"This resume is only conditionally recommended for "
                f"{match_data.get('job_title') or 'the target role'} "
                f"({float(match_data.get('overall_match') or 0):.0f}% match)."
            )
        skill_match_pct = float(match_data.get('skill_match_pct') or 0)
        keyword_match_pct = float(match_data.get('keyword_match_pct') or 0)
        if skill_match_pct and skill_match_pct < 40:
            job_match_issues.append(f'Skill match against the job description is {skill_match_pct:.0f}%.')
        if keyword_match_pct and keyword_match_pct < 40:
            job_match_issues.append(f'Job-description keyword alignment is {keyword_match_pct:.0f}%.')
        if jd_missing:
            job_match_issues.append('Missing job-required skills: ' + ', '.join(jd_missing[:8]) + '.')
        role_analysis = match_data.get('role_analysis') or {}
        if role_analysis and not role_analysis.get('role_matched', True):
            job_match_issues.append(
                f"Role/domain alignment with {role_analysis.get('jd_domain', 'the job field')} is weak."
            )

        if job_match_issues:
            why_parts.append('the resume does not fully align with the analyzed job description')

    if not why_parts:
        if risk_level == 'Low':
            why = (
                f'This resume has a relatively strong ATS score ({overall:.0f}/100). '
                'Remaining gaps below can still cause screening issues at some employers.'
            )
        else:
            why = (
                f'This resume may be filtered by ATS because the detected content scored '
                f'{overall:.0f}/100 overall.'
            )
    else:
        why = 'This resume may be rejected by ATS screening because ' + '; '.join(why_parts) + '.'

    improvements = _build_improvement_plan(extracted, ats_scores, has_job_match, match_data or {})

    return {
        'has_job_match': has_job_match,
        'job_title': (match_data or {}).get('job_title', ''),
        'risk_level': risk_level,
        'risk_color': risk_color,
        'risk_percent': risk_percent,
        'why': why,
        'critical_issues': critical_issues,
        'missing_skills': missing_skills[:12],
        'missing_skills_source': skills_label,
        'missing_keywords': missing_keywords[:12],
        'missing_keywords_source': keywords_label,
        'formatting_issues': formatting_issues,
        'weak_sections': weak_sections,
        'job_match_issues': job_match_issues,
        'improvements': improvements,
        'disclaimer': (
            'This is an AI screening explanation based on the uploaded resume'
            + (' and the job description you matched to this same resume.' if has_job_match else '.')
            + ' It does not represent an actual employer decision.'
        ),
    }


def _build_improvement_plan(extracted, ats_scores, has_job_match, match_data) -> list:
    """Problem / why / improvement / priority / qualitative impact — from this resume only."""
    items = []

    if (ats_scores.get('keyword_score') or 0) < 55:
        items.append({
            'problem': 'Keyword coverage is below a typical ATS-friendly range',
            'why': 'Applicant tracking systems rank resumes that repeat role-relevant terms used in job posts.',
            'improvement': 'Add role-relevant technical terms and lead bullets with action verbs already used in your work (developed, implemented, delivered).',
            'priority': 'High',
            'impact': 'Adding missing technical keywords can improve ATS keyword coverage.',
        })

    tech = (extracted.get('skills') or {}).get('technical') or []
    if len(tech) < 8:
        items.append({
            'problem': 'Few technical skills were extracted from this resume',
            'why': 'Skill lists are a primary ATS matching field.',
            'improvement': 'Add a dedicated Skills section with the tools you actually used in jobs and projects.',
            'priority': 'High',
            'impact': 'A clearer skills section can improve the skills and keyword components of the ATS score.',
        })

    if not extracted.get('summary') or (ats_scores.get('summary_score') or 0) < 50:
        items.append({
            'problem': 'Professional summary is missing or too short',
            'why': 'The summary is often the first parsed block and should state target role plus core skills.',
            'improvement': 'Write 3–5 sentences naming your target role, years of experience (if any), and 4–6 core skills.',
            'priority': 'High',
            'impact': 'A complete summary can improve the summary score and keyword density.',
        })

    if not extracted.get('projects'):
        items.append({
            'problem': 'No projects section was detected',
            'why': 'Projects demonstrate applied skills when work history is thin.',
            'improvement': 'Add 2–3 projects with the stack used and one measurable outcome each.',
            'priority': 'Medium',
            'impact': 'Documented projects can strengthen the projects component of the ATS analysis.',
        })

    if (extracted.get('measurable_achievements_count') or 0) < 2:
        items.append({
            'problem': 'Few quantified achievements were found',
            'why': 'Numbers help both ATS keyword hits and recruiter credibility.',
            'improvement': 'Rewrite bullets with metrics (%, time saved, users, revenue, class rank) from real work.',
            'priority': 'Medium',
            'impact': 'Quantified bullets can improve measurable-achievement and experience scoring.',
        })

    if (ats_scores.get('formatting_score') or 0) < 60 or (ats_scores.get('sections_missing') or []):
        items.append({
            'problem': 'ATS formatting or standard section headers are incomplete',
            'why': 'Parsers look for common headings; tables and images often drop text.',
            'improvement': 'Use plain headings: Summary, Skills, Experience, Education, Projects. Export as text-based PDF.',
            'priority': 'High',
            'impact': 'Standard headings can improve ATS formatting and section detection.',
        })

    if not extracted.get('certifications'):
        items.append({
            'problem': 'No certifications were detected',
            'why': 'Some ATS keyword lists include certification names from job posts.',
            'improvement': 'List completed courses or certifications with the issuer and year.',
            'priority': 'Low',
            'impact': 'Listing real certifications can add keywords that some job descriptions require.',
        })

    if has_job_match and (match_data.get('missing_skills') or []):
        missing = ', '.join((match_data.get('missing_skills') or [])[:6])
        items.append({
            'problem': f'Skills required by the matched job description are absent: {missing}',
            'why': 'Job-specific ATS filters reject resumes that omit required skill tokens.',
            'improvement': f'Only add skills you actually have. Where true, include: {missing}.',
            'priority': 'High',
            'impact': 'Aligning skills with the analyzed job description can improve job-match keyword overlap.',
        })

    if not extracted.get('linkedin'):
        items.append({
            'problem': 'LinkedIn URL was not detected',
            'why': 'Recruiters and some ATS profiles expect a professional profile link.',
            'improvement': 'Add your LinkedIn URL in the contact line.',
            'priority': 'Low',
            'impact': 'A profile URL does not change core ATS math much, but it reduces recruiter drop-off.',
        })

    priority_rank = {'High': 0, 'Medium': 1, 'Low': 2}
    items.sort(key=lambda x: priority_rank.get(x['priority'], 9))
    return items[:8]
