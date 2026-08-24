"""
LinkedIn Optimization Service
Analyzes resume and generates LinkedIn profile optimization suggestions.
"""
import re
import logging

logger = logging.getLogger(__name__)


def generate_linkedin_report(extracted: dict, ats_scores: dict) -> dict:
    """Generate comprehensive LinkedIn optimization report from resume data."""

    skills = extracted.get('skills', {}).get('technical', [])
    soft_skills = extracted.get('skills', {}).get('soft', [])
    name = extracted.get('name', 'Professional')
    summary = extracted.get('summary', '')
    experience = extracted.get('experience', [])
    education = extracted.get('education', [])
    projects = extracted.get('projects', [])
    certs = extracted.get('certifications', [])
    has_linkedin = bool(extracted.get('linkedin'))

    # ── Profile Score ─────────────────────────────────────────────────────
    score = 0
    score_breakdown = {}

    # Name and basic info
    if name:
        score += 10
        score_breakdown['Name/Identity'] = 10
    # Summary / About section
    if summary and len(summary.split()) >= 30:
        score += 15
        score_breakdown['About Section'] = 15
    elif summary:
        score += 8
        score_breakdown['About Section'] = 8
    else:
        score_breakdown['About Section'] = 0

    # Skills
    if len(skills) >= 10:
        score += 15
        score_breakdown['Skills'] = 15
    elif len(skills) >= 5:
        score += 10
        score_breakdown['Skills'] = 10
    else:
        score += 3
        score_breakdown['Skills'] = 3

    # Experience
    if len(experience) >= 2:
        score += 15
        score_breakdown['Experience'] = 15
    elif experience:
        score += 10
        score_breakdown['Experience'] = 10
    else:
        score_breakdown['Experience'] = 0

    # Education
    if education:
        score += 10
        score_breakdown['Education'] = 10
    else:
        score_breakdown['Education'] = 0

    # Projects
    if len(projects) >= 2:
        score += 10
        score_breakdown['Featured Projects'] = 10
    elif projects:
        score += 5
        score_breakdown['Featured Projects'] = 5
    else:
        score_breakdown['Featured Projects'] = 0

    # Certifications
    if certs:
        score += 10
        score_breakdown['Certifications'] = 10
    else:
        score_breakdown['Certifications'] = 0

    # Profile photo (can't detect, assume not present)
    score_breakdown['Profile Photo'] = 0

    # LinkedIn URL
    if has_linkedin:
        score += 5
        score_breakdown['Custom URL'] = 5

    score = min(100, score)

    # Score label
    if score >= 85:
        score_label = 'All-Star Profile'
    elif score >= 70:
        score_label = 'Expert Profile'
    elif score >= 55:
        score_label = 'Advanced Profile'
    elif score >= 40:
        score_label = 'Intermediate Profile'
    else:
        score_label = 'Beginner Profile'

    # ── Headline Suggestions ──────────────────────────────────────────────
    top_skills = skills[:3] if skills else ['Professional']
    edu_short = education[0][:40] if education else 'Graduate'

    headlines = [
        f'{" | ".join(top_skills[:2])} Developer | Building {top_skills[0] if top_skills else "Tech"} Solutions',
        f'Aspiring {top_skills[0] if top_skills else "Software"} Engineer | {edu_short}',
        f'{top_skills[0] if top_skills else "Tech"} Enthusiast | {" | ".join(top_skills[1:3]) if len(top_skills) > 1 else "Problem Solver"}',
        f'Software Engineer in Training | Passionate about {top_skills[0] if top_skills else "Technology"}',
    ]

    # ── About Section Suggestions ─────────────────────────────────────────
    about_suggestions = []
    if not summary or len(summary.split()) < 30:
        about_template = (
            f"Results-driven {top_skills[0] if top_skills else 'technology'} professional with a passion for "
            f"building impactful solutions. "
            f"{'Experienced in ' + ', '.join(top_skills[:3]) + '.' if top_skills else ''} "
            f"{'Education background in ' + education[0][:50] + '.' if education else ''} "
            f"Looking to leverage my skills to contribute to a high-performing team."
        )
        about_suggestions.append({
            'title': 'Suggested About Section Template',
            'content': about_template,
        })

    about_tips = [
        'Start with a strong opening statement about your expertise or passion.',
        'Mention your top 3 technical skills in the first paragraph.',
        'Include your education and notable achievements.',
        'Add a call-to-action: "Open to opportunities in [domain]."',
        'Use keywords recruiters search for in your domain.',
        'Keep it between 150–250 words for optimal readability.',
    ]

    # ── Featured Skills ───────────────────────────────────────────────────
    top_skills_for_linkedin = (skills + soft_skills)[:15]

    # ── Recruiter Visibility Tips ─────────────────────────────────────────
    visibility_tips = [
        {'title': 'Turn on "Open to Work"',
         'description': 'Enable the "Open to Work" feature to signal recruiters you are job hunting.',
         'priority': 'High'},
        {'title': 'Customize your LinkedIn URL',
         'description': 'Go to Settings → Edit public profile URL. Use linkedin.com/in/yourname',
         'priority': 'High'},
        {'title': 'Add Profile Photo',
         'description': 'Profiles with photos get 21x more views. Use a professional headshot.',
         'priority': 'Critical'},
        {'title': 'Complete All Sections',
         'description': 'LinkedIn gives 40x more messages to All-Star profiles. Complete every section.',
         'priority': 'High'},
        {'title': 'Request Recommendations',
         'description': 'Ask professors, project partners, or mentors for LinkedIn recommendations.',
         'priority': 'Medium'},
        {'title': 'Engage Weekly',
         'description': 'Post or comment on industry content 2–3x per week to increase visibility.',
         'priority': 'Medium'},
        {'title': 'Add Skills & Take Assessments',
         'description': 'Take LinkedIn skill assessments to earn badges — increases recruiter confidence.',
         'priority': 'High'},
        {'title': 'Connect Strategically',
         'description': 'Connect with professionals in your target domain (500+ connections goal).',
         'priority': 'Medium'},
    ]

    # ── Missing Sections ──────────────────────────────────────────────────
    missing_sections = []
    if not summary:
        missing_sections.append('About/Summary section')
    if not experience:
        missing_sections.append('Work Experience')
    if not certs:
        missing_sections.append('Certifications')
    if not projects:
        missing_sections.append('Featured Projects')
    missing_sections.extend(['Profile Photo', 'Cover Image', 'Volunteer Work'])

    # ── Networking Tips ───────────────────────────────────────────────────
    networking_tips = [
        'Join LinkedIn groups related to your target role or industry.',
        f'Follow companies you want to work for (e.g., companies hiring {top_skills[0] if top_skills else "developers"}).',
        'Message alumni from your college who work in your target companies.',
        'Comment thoughtfully on posts by industry leaders — visibility compounds.',
        'Share your projects with context — what you built, why, and what you learned.',
        'Participate in #OpenToWork communities on LinkedIn.',
    ]

    return {
        'profile_score': score,
        'score_label': score_label,
        'score_breakdown': score_breakdown,
        'headlines': headlines,
        'about_tips': about_tips,
        'about_suggestions': about_suggestions,
        'featured_skills': top_skills_for_linkedin,
        'visibility_tips': visibility_tips,
        'missing_sections': missing_sections,
        'networking_tips': networking_tips,
        'has_linkedin_url': has_linkedin,
        'profile_completeness': round(score, 0),
    }
