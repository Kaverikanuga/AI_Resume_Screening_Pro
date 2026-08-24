"""
Naukri Optimization Service
Analyzes resume and generates Naukri.com profile optimization suggestions.
"""
import re
import logging

logger = logging.getLogger(__name__)


def generate_naukri_report(extracted: dict, ats_scores: dict) -> dict:
    """Generate comprehensive Naukri profile optimization report."""

    skills = extracted.get('skills', {}).get('technical', [])
    soft_skills = extracted.get('skills', {}).get('soft', [])
    name = extracted.get('name', 'Professional')
    summary = extracted.get('summary', '')
    experience = extracted.get('experience', [])
    education = extracted.get('education', [])
    projects = extracted.get('projects', [])
    certs = extracted.get('certifications', [])
    word_count = extracted.get('word_count', 0)

    # ── Naukri Resume Score ───────────────────────────────────────────────
    score = 0
    score_breakdown = {}

    # Personal info completeness
    personal_score = 0
    if name:
        personal_score += 5
    if extracted.get('email'):
        personal_score += 5
    if extracted.get('phone'):
        personal_score += 5
    if extracted.get('location'):
        personal_score += 3
    score += personal_score
    score_breakdown['Personal Information'] = personal_score

    # Resume content
    content_score = 0
    if summary and len(summary.split()) >= 20:
        content_score += 10
    if experience:
        content_score += min(20, len(experience) * 7)
    if education:
        content_score += 10
    if projects:
        content_score += min(10, len(projects) * 4)
    score += content_score
    score_breakdown['Resume Content'] = content_score

    # Skills section
    skills_score = min(20, len(skills) * 2)
    score += skills_score
    score_breakdown['Key Skills'] = skills_score

    # Certifications
    cert_score = min(10, len(certs) * 3) if certs else 0
    score += cert_score
    score_breakdown['Certifications'] = cert_score

    # Resume length
    if 300 <= word_count <= 800:
        score += 5
        score_breakdown['Resume Length'] = 5
    else:
        score_breakdown['Resume Length'] = 0

    score = min(100, score)

    # Score label
    if score >= 80:
        score_label = 'Excellent'
        visibility = 'High'
    elif score >= 60:
        score_label = 'Good'
        visibility = 'Moderate'
    elif score >= 40:
        score_label = 'Average'
        visibility = 'Low'
    else:
        score_label = 'Needs Improvement'
        visibility = 'Very Low'

    # ── Search Visibility ─────────────────────────────────────────────────
    keyword_density = _calculate_keyword_density(skills, summary, experience)

    # ── Missing Keywords ──────────────────────────────────────────────────
    naukri_popular_keywords = [
        'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'SQL', 'MongoDB',
        'Machine Learning', 'Data Science', 'AWS', 'Docker', 'Kubernetes',
        'REST API', 'Git', 'Agile', 'Spring Boot', 'Django', 'Flask',
        'TypeScript', 'Angular', 'Vue.js', 'PostgreSQL', 'Redis', 'Kafka',
    ]
    resume_skills_lower = {s.lower() for s in skills}
    missing_keywords = [
        kw for kw in naukri_popular_keywords if kw.lower() not in resume_skills_lower
    ][:10]

    # ── Ranking Improvements ──────────────────────────────────────────────
    ranking_tips = [
        {
            'title': 'Add Key Skills Section',
            'description': 'Naukri searches heavily rely on the Skills section. Add 10–20 specific skills.',
            'impact': 'High',
        },
        {
            'title': 'Update Resume Regularly',
            'description': 'Update your Naukri resume every 2 weeks to stay at the top of search results.',
            'impact': 'High',
        },
        {
            'title': 'Set Job Preferences',
            'description': 'Set preferred locations, job function, industry, and salary range to attract relevant recruiters.',
            'impact': 'High',
        },
        {
            'title': 'Add Video Profile',
            'description': 'Naukri video profiles get 60% more views. Record a 60-second introduction.',
            'impact': 'Medium',
        },
        {
            'title': 'Complete Naukri Resume Score',
            'description': 'Aim for 80%+ Naukri resume score to appear in premium recruiter searches.',
            'impact': 'High',
        },
        {
            'title': 'Set Notice Period Correctly',
            'description': 'Update availability/notice period — recruiters filter by this.',
            'impact': 'Medium',
        },
        {
            'title': 'Add Desired Salary',
            'description': 'Adding expected salary helps recruiters match you to appropriate openings.',
            'impact': 'Medium',
        },
    ]

    # ── Recruiter Visibility Tips ─────────────────────────────────────────
    recruiter_tips = [
        'Set profile to "Actively looking" — increases recruiter contact rate by 3x.',
        'Respond to recruiters within 24 hours — Naukri tracks response rate.',
        'Apply to at least 5–10 jobs per week to keep profile active.',
        'Use Naukri\'s Job Alert feature for instant notifications.',
        'Mark yourself "Available Immediately" if you are a fresher.',
        'Complete Naukri skill assessments to earn verified badges.',
        'Add a professional photo — profiles with photos get 70% more responses.',
    ]

    # ── Recommendations ───────────────────────────────────────────────────
    recommendations = []
    if not summary or len(summary.split()) < 20:
        recommendations.append('Add a strong career objective (3–4 sentences) — Naukri uses this for search ranking.')
    if len(skills) < 8:
        recommendations.append(f'Add at least {8 - len(skills)} more technical skills to improve search ranking.')
    if not experience:
        recommendations.append('Add internships, projects, or freelance work under work experience.')
    if not certs:
        recommendations.append('List any completed courses or certifications (Coursera, NPTEL, Udemy).')
    if not extracted.get('phone'):
        recommendations.append('Add a contact number — required for Naukri recruiter calls.')
    if word_count < 200:
        recommendations.append('Your resume is too brief — expand each section for better ATS parsing.')

    return {
        'naukri_score': score,
        'score_label': score_label,
        'score_breakdown': score_breakdown,
        'search_visibility': visibility,
        'keyword_density': keyword_density,
        'missing_keywords': missing_keywords,
        'ranking_tips': ranking_tips,
        'recruiter_tips': recruiter_tips,
        'recommendations': recommendations,
        'skills_count': len(skills),
        'experience_count': len(experience),
        'projects_count': len(projects),
        'certs_count': len(certs),
    }


def _calculate_keyword_density(skills: list, summary: str, experience: list) -> dict:
    """Calculate keyword density for Naukri search optimization."""
    all_text = summary + ' ' + ' '.join(experience)
    word_count = len(all_text.split()) if all_text.strip() else 1

    density_score = min(100, (len(skills) / max(word_count / 10, 1)) * 100)

    if density_score >= 70:
        level = 'Optimal'
        color = 'success'
    elif density_score >= 50:
        level = 'Moderate'
        color = 'warning'
    else:
        level = 'Low'
        color = 'danger'

    return {
        'score': round(density_score, 1),
        'level': level,
        'color': color,
        'skills_count': len(skills),
        'description': f'{len(skills)} skills detected — aim for 12–18 skills for optimal visibility.',
    }
