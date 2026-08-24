"""
ATS Analyzer Service
Calculates ATS compatibility scores and provides detailed feedback.
"""
import re
import math
import logging

logger = logging.getLogger(__name__)

# ── Scoring weights ──────────────────────────────────────────────────────

WEIGHTS = {
    'skills': 0.30,
    'keyword': 0.20,
    'formatting': 0.15,
    'education': 0.10,
    'experience': 0.10,
    'projects': 0.08,
    'summary': 0.04,
    'measurable': 0.03,
}

# High-frequency ATS keywords that matter across all domains
UNIVERSAL_ATS_KEYWORDS = [
    'results', 'collaborated', 'managed', 'developed', 'implemented',
    'delivered', 'achieved', 'improved', 'increased', 'reduced',
    'team', 'project', 'experience', 'skills', 'education',
]

FORMATTING_GOOD_SIGNS = [
    'email', 'phone', 'linkedin', 'github', 'education', 'experience',
    'skills', 'projects', 'certifications', 'summary',
]

FORMATTING_BAD_SIGNS = [
    r'[^\x00-\x7F]',  # Non-ASCII that may confuse ATS
]

ATS_FRIENDLY_FONTS = ['calibri', 'arial', 'times', 'georgia', 'garamond']

ACTION_VERB_LIST = [
    'developed', 'implemented', 'designed', 'built', 'created', 'managed',
    'led', 'spearheaded', 'launched', 'delivered', 'achieved', 'improved',
    'increased', 'reduced', 'optimized', 'automated', 'collaborated',
    'coordinated', 'analyzed', 'researched', 'engineered', 'deployed',
    'integrated', 'maintained', 'supervised', 'mentored', 'trained',
    'resolved', 'streamlined', 'generated', 'established', 'oversaw',
]


def score_skills(extracted: dict) -> dict:
    """Score based on number and variety of skills."""
    tech_skills = extracted.get('skills', {}).get('technical', [])
    soft_skills = extracted.get('skills', {}).get('soft', [])
    total_skills = len(tech_skills) + len(soft_skills)

    # Score: up to 100
    raw_score = min(100, (total_skills / 20) * 100)
    # Bonus for having both tech and soft
    if tech_skills and soft_skills:
        raw_score = min(100, raw_score + 5)

    issues = []
    strengths = []
    if total_skills < 5:
        issues.append('Very few skills listed — add at least 10–15 relevant skills.')
    elif total_skills < 10:
        issues.append('Skills section could be stronger — aim for 10+ technical skills.')
    else:
        strengths.append(f'Good variety of skills ({total_skills} skills listed).')

    if not soft_skills:
        issues.append('No soft skills listed — add communication, teamwork, leadership, etc.')
    else:
        strengths.append(f'{len(soft_skills)} soft skills demonstrate well-rounded profile.')

    return {
        'score': round(raw_score, 1),
        'tech_count': len(tech_skills),
        'soft_count': len(soft_skills),
        'total': total_skills,
        'issues': issues,
        'strengths': strengths,
    }


def score_keywords(text: str, extracted: dict) -> dict:
    """Score keyword density and usage."""
    if not text:
        return {'score': 0, 'issues': ['No text found in resume.'], 'strengths': []}

    text_lower = text.lower()
    word_count = len(text_lower.split())

    # Count ATS keywords
    found = [kw for kw in UNIVERSAL_ATS_KEYWORDS if kw in text_lower]
    keyword_density = len(found) / len(UNIVERSAL_ATS_KEYWORDS) * 100

    # Action verbs
    action_verbs_found = extracted.get('action_verbs', [])
    action_score = min(100, len(action_verbs_found) * 10)

    combined_score = (keyword_density * 0.5) + (action_score * 0.5)

    issues = []
    strengths = []

    if len(action_verbs_found) < 3:
        issues.append('Too few action verbs — use more dynamic verbs like "developed", "achieved", "led".')
    else:
        strengths.append(f'{len(action_verbs_found)} strong action verbs found.')

    if word_count < 200:
        issues.append('Resume is too short — ATS may not find enough content to evaluate.')
    elif word_count > 1200:
        issues.append('Resume may be too long — consider condensing to 1–2 pages.')
    else:
        strengths.append(f'Good resume length ({word_count} words).')

    return {
        'score': round(min(100, combined_score), 1),
        'action_verbs': action_verbs_found,
        'keywords_found': found,
        'word_count': word_count,
        'issues': issues,
        'strengths': strengths,
    }


def score_formatting(text: str, extracted: dict) -> dict:
    """Score formatting and structure."""
    issues = []
    strengths = []
    score = 60  # Base score

    text_lower = text.lower() if text else ''

    # Check for key sections
    sections_found = []
    sections_missing = []
    required_sections = ['education', 'experience', 'skills', 'projects']
    optional_sections = ['summary', 'certifications', 'achievements', 'languages']

    for sec in required_sections:
        if any(kw in text_lower for kw in [sec, sec + 's']):
            sections_found.append(sec)
            score += 5
        else:
            sections_missing.append(sec)

    for sec in optional_sections:
        if any(kw in text_lower for kw in [sec, sec + 's']):
            sections_found.append(sec)
            score += 2

    # Check contact information
    has_email = bool(extracted.get('email'))
    has_phone = bool(extracted.get('phone'))
    has_name = bool(extracted.get('name'))

    if has_email:
        score += 3
        strengths.append('Email address present.')
    else:
        issues.append('Email address not found — ensure it is included.')

    if has_phone:
        score += 3
        strengths.append('Phone number present.')
    else:
        issues.append('Phone number not found — ensure it is included.')

    if has_name:
        score += 5
        strengths.append('Candidate name detected.')
    else:
        issues.append('Name not clearly detected — ensure it is at the top of the resume.')

    if sections_missing:
        issues.append(f'Missing sections: {", ".join(s.capitalize() for s in sections_missing)}.')

    if len(sections_found) >= 4:
        strengths.append(f'{len(sections_found)} key sections found: well-structured resume.')

    # Length check
    word_count = len(text.split()) if text else 0
    if word_count < 150:
        issues.append('Resume content is too brief for ATS to parse effectively.')
        score -= 10
    elif 300 <= word_count <= 900:
        strengths.append('Resume length is ideal for ATS parsing.')
        score += 5

    return {
        'score': round(min(100, max(0, score)), 1),
        'sections_found': sections_found,
        'sections_missing': sections_missing,
        'has_email': has_email,
        'has_phone': has_phone,
        'has_name': has_name,
        'issues': issues,
        'strengths': strengths,
    }


def score_grammar_readability(text: str) -> dict:
    """Estimate grammar and readability score heuristically."""
    if not text:
        return {'grammar_score': 50, 'readability_score': 50, 'issues': [], 'strengths': []}

    issues = []
    strengths = []
    grammar_score = 75
    readability_score = 70

    sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    avg_sentence_len = (sum(len(s.split()) for s in sentences) / len(sentences)) if sentences else 0

    if avg_sentence_len > 25:
        issues.append('Some sentences are too long — keep bullets concise (under 20 words).')
        readability_score -= 10
    elif avg_sentence_len < 5 and avg_sentence_len > 0:
        issues.append('Many very short sentences — add more context to experience descriptions.')
        readability_score -= 5
    else:
        strengths.append('Sentence length is appropriate for professional context.')

    # Check for personal pronouns (ATS unfriendly)
    pronoun_count = len(re.findall(r'\b(I|me|my|myself|we|our)\b', text, re.IGNORECASE))
    if pronoun_count > 5:
        issues.append('Avoid using personal pronouns (I, me, my) — use action verb-led bullets.')
        grammar_score -= 8

    return {
        'grammar_score': round(min(100, grammar_score), 1),
        'readability_score': round(min(100, readability_score), 1),
        'avg_sentence_len': round(avg_sentence_len, 1),
        'issues': issues,
        'strengths': strengths,
    }


def score_education(extracted: dict) -> dict:
    """Score education section."""
    education = extracted.get('education', [])
    score = 0
    issues = []
    strengths = []

    if not education:
        issues.append('No education information detected — add degree, institution, year.')
        return {'score': 0, 'issues': issues, 'strengths': strengths}

    score = min(100, len(education) * 40 + 20)
    strengths.append(f'{len(education)} education entry(ies) found.')

    # Check for CGPA/percentage
    edu_text = ' '.join(education).lower()
    if re.search(r'(cgpa|gpa|percentage|%)', edu_text):
        score = min(100, score + 10)
        strengths.append('Academic performance (CGPA/%) mentioned.')
    else:
        issues.append('Consider adding your CGPA or percentage to education entries.')

    return {'score': round(score, 1), 'count': len(education), 'issues': issues, 'strengths': strengths}


def score_experience(extracted: dict) -> dict:
    """Score experience section."""
    experience = extracted.get('experience', [])
    score = 0
    issues = []
    strengths = []

    if not experience:
        issues.append('No work experience or internship found — add any relevant experience.')
        return {'score': 30, 'issues': issues, 'strengths': strengths}

    score = min(100, len(experience) * 25 + 25)
    strengths.append(f'{len(experience)} experience entry(ies) found.')

    exp_text = ' '.join(experience).lower()
    measurable = len(re.findall(r'\d+\s*(?:%|percent|x|times|k\b|lakh|crore|million)', exp_text))
    if measurable > 0:
        score = min(100, score + 10)
        strengths.append(f'{measurable} measurable achievement(s) in experience section.')
    else:
        issues.append('Add quantifiable achievements (%, numbers) to experience descriptions.')

    return {'score': round(score, 1), 'count': len(experience), 'issues': issues, 'strengths': strengths}


def score_projects(extracted: dict) -> dict:
    """Score projects section."""
    projects = extracted.get('projects', [])
    score = 0
    issues = []
    strengths = []

    if not projects:
        issues.append('No projects found — add academic or personal projects with tech stack.')
        return {'score': 20, 'issues': issues, 'strengths': strengths}

    score = min(100, len(projects) * 25 + 25)
    strengths.append(f'{len(projects)} project(s) found.')

    # Check for tech mentions
    tech_mentioned = any(
        any(tech in proj.lower() for tech in ['python', 'java', 'react', 'node', 'ml', 'ai', 'sql'])
        for proj in projects
    )
    if tech_mentioned:
        score = min(100, score + 10)
        strengths.append('Projects mention specific technologies.')
    else:
        issues.append('Specify technologies used in projects (e.g., Python, React, MySQL).')

    return {'score': round(score, 1), 'count': len(projects), 'issues': issues, 'strengths': strengths}


def score_summary(extracted: dict) -> dict:
    """Score professional summary."""
    summary = extracted.get('summary', '')
    issues = []
    strengths = []

    if not summary:
        issues.append('No professional summary found — add a 2–3 sentence career objective.')
        return {'score': 20, 'issues': issues, 'strengths': strengths}

    word_count = len(summary.split())
    if word_count < 20:
        issues.append('Professional summary is too short — expand to 30–60 words.')
        score = 40
    elif word_count > 100:
        issues.append('Professional summary is too long — keep it under 80 words.')
        score = 60
    else:
        strengths.append(f'Professional summary is well-sized ({word_count} words).')
        score = 80

    return {'score': round(score, 1), 'word_count': word_count, 'issues': issues, 'strengths': strengths}


def calculate_ats_score(extracted: dict, raw_text: str) -> dict:
    """
    Main ATS analysis function.
    Returns a comprehensive dict with scores, strengths, weaknesses, suggestions.
    """
    # Component scores
    skills_result = score_skills(extracted)
    keyword_result = score_keywords(raw_text, extracted)
    formatting_result = score_formatting(raw_text, extracted)
    grammar_result = score_grammar_readability(raw_text)
    education_result = score_education(extracted)
    experience_result = score_experience(extracted)
    projects_result = score_projects(extracted)
    summary_result = score_summary(extracted)

    # Weighted overall ATS score
    overall = (
        skills_result['score'] * WEIGHTS['skills'] +
        keyword_result['score'] * WEIGHTS['keyword'] +
        formatting_result['score'] * WEIGHTS['formatting'] +
        education_result['score'] * WEIGHTS['education'] +
        experience_result['score'] * WEIGHTS['experience'] +
        projects_result['score'] * WEIGHTS['projects'] +
        summary_result['score'] * WEIGHTS['summary'] +
        min(100, extracted.get('measurable_achievements_count', 0) * 20) * WEIGHTS['measurable']
    )
    overall = round(min(100, max(0, overall)), 1)

    # Aggregate strengths and weaknesses
    all_strengths = (
        skills_result['strengths'] + keyword_result['strengths'] +
        formatting_result['strengths'] + education_result['strengths'] +
        experience_result['strengths'] + projects_result['strengths'] +
        summary_result['strengths'] + grammar_result['strengths']
    )
    all_issues = (
        skills_result['issues'] + keyword_result['issues'] +
        formatting_result['issues'] + education_result['issues'] +
        experience_result['issues'] + projects_result['issues'] +
        summary_result['issues'] + grammar_result['issues']
    )

    # ATS compatibility label
    if overall >= 80:
        ats_label = 'Excellent'
        ats_color = 'success'
    elif overall >= 65:
        ats_label = 'Good'
        ats_color = 'primary'
    elif overall >= 50:
        ats_label = 'Average'
        ats_color = 'warning'
    elif overall >= 35:
        ats_label = 'Below Average'
        ats_color = 'warning'
    else:
        ats_label = 'Poor'
        ats_color = 'danger'

    # Improvement suggestions
    suggestions = []
    if skills_result['tech_count'] < 10:
        suggestions.append('Add more specific technical skills relevant to your target role.')
    if not extracted.get('summary'):
        suggestions.append('Write a compelling professional summary (3–5 sentences).')
    if not extracted.get('certifications'):
        suggestions.append('Add professional certifications or online courses (Coursera, Udemy).')
    if extracted.get('measurable_achievements_count', 0) < 3:
        suggestions.append('Quantify achievements with numbers: "Increased performance by 40%".')
    if not extracted.get('projects'):
        suggestions.append('Add 2–3 relevant projects with tech stack and outcomes.')
    if len(keyword_result.get('action_verbs', [])) < 5:
        suggestions.append('Lead every experience bullet with a strong action verb.')
    if not extracted.get('linkedin'):
        suggestions.append('Add your LinkedIn profile URL.')
    if not extracted.get('github') and any(
        s in ' '.join(extracted.get('skills', {}).get('technical', [])).lower()
        for s in ['python', 'java', 'react', 'node', 'code']
    ):
        suggestions.append('Add your GitHub profile URL — important for tech roles.')

    word_count = keyword_result.get('word_count', 0)
    incomplete = word_count < 40
    incomplete_reason = (
        'Very little text could be extracted from this PDF. It may be image-based or poorly encoded. '
        'Only fields and metrics that were actually detected are shown.'
        if incomplete else ''
    )

    professional_strength_score = compute_professional_strength(
        skills_result['score'],
        experience_result['score'],
        projects_result['score'],
        extracted.get('measurable_achievements_count', 0),
        len(keyword_result.get('action_verbs', [])),
    )
    factual_strengths = detect_factual_strengths(extracted)
    gaps = collect_ats_gaps(extracted, raw_text, keyword_result, formatting_result, skills_result)

    return {
        'overall_score': overall,
        'keyword_score': keyword_result['score'],
        'formatting_score': formatting_result['score'],
        'grammar_score': grammar_result['grammar_score'],
        'readability_score': grammar_result['readability_score'],
        'skills_score': skills_result['score'],
        'education_score': education_result['score'],
        'experience_score': experience_result['score'],
        'projects_score': projects_result['score'],
        'summary_score': summary_result['score'],
        'professional_strength_score': professional_strength_score,
        'ats_label': ats_label,
        'ats_color': ats_color,
        'strengths': factual_strengths or all_strengths[:8],
        'weaknesses': all_issues[:8],
        'suggestions': suggestions[:8],
        'action_verbs': keyword_result.get('action_verbs', []),
        'keywords_found': keyword_result.get('keywords_found', []),
        'word_count': word_count,
        'sections_found': formatting_result.get('sections_found', []),
        'sections_missing': formatting_result.get('sections_missing', []),
        'measurable_achievements': extracted.get('measurable_achievements_count', 0),
        'incomplete': incomplete,
        'incomplete_reason': incomplete_reason,
        'missing_keywords_general': gaps['missing_keywords_general'],
        'weak_skill_areas': gaps['weak_skill_areas'],
        'missing_sections_detail': gaps['missing_sections_detail'],
        'ats_gaps': gaps['other_gaps'],
        'component_scores': {
            'Skills': skills_result['score'],
            'Keywords': keyword_result['score'],
            'Formatting': formatting_result['score'],
            'Education': education_result['score'],
            'Experience': experience_result['score'],
            'Projects': projects_result['score'],
            'Summary': summary_result['score'],
        }
    }


def compute_professional_strength(skills_score, experience_score, projects_score,
                                  measurable_count, action_verb_count) -> float:
    """Composite professional-strength score from detected resume evidence only."""
    measurable_score = min(100, (measurable_count or 0) * 20)
    action_score = min(100, (action_verb_count or 0) * 10)
    score = (
        (experience_score or 0) * 0.30 +
        (skills_score or 0) * 0.30 +
        (projects_score or 0) * 0.20 +
        measurable_score * 0.10 +
        action_score * 0.10
    )
    return round(min(100, max(0, score)), 1)


def detect_factual_strengths(extracted: dict) -> list:
    """Strengths that are true only if the parser found them on this resume."""
    extracted = extracted or {}
    skills = extracted.get('skills') or {}
    strengths = []
    if extracted.get('name'):
        strengths.append('Candidate name detected')
    if extracted.get('email'):
        strengths.append('Email detected')
    if extracted.get('phone'):
        strengths.append('Phone detected')
    if extracted.get('linkedin'):
        strengths.append('LinkedIn profile URL detected')
    if extracted.get('github'):
        strengths.append('GitHub profile URL detected')
    if extracted.get('summary'):
        strengths.append('Professional summary found')
    if extracted.get('education'):
        strengths.append('Education section found')
    if extracted.get('experience'):
        strengths.append('Experience section found')
    if extracted.get('projects'):
        strengths.append('Projects found')
    if skills.get('technical'):
        strengths.append(f"Technical skills found ({len(skills.get('technical', []))})")
    if skills.get('soft'):
        strengths.append(f"Soft skills found ({len(skills.get('soft', []))})")
    if extracted.get('certifications'):
        strengths.append('Certifications found')
    if extracted.get('achievements'):
        strengths.append('Achievements found')
    if extracted.get('action_verbs'):
        strengths.append(f"{len(extracted.get('action_verbs', []))} action verbs detected")
    if extracted.get('measurable_achievements_count'):
        strengths.append('Measurable achievements detected')
    return strengths


def collect_ats_gaps(extracted, raw_text, keyword_result, formatting_result, skills_result) -> dict:
    """General ATS gaps from this resume only (not a job-description comparison)."""
    extracted = extracted or {}
    text_lower = (raw_text or '').lower()
    found_keywords = set(k.lower() for k in (keyword_result.get('keywords_found') or []))
    missing_keywords_general = [
        kw for kw in UNIVERSAL_ATS_KEYWORDS
        if kw.lower() not in found_keywords and kw.lower() not in text_lower
    ]

    weak_skill_areas = []
    tech_count = skills_result.get('tech_count', 0)
    soft_count = skills_result.get('soft_count', 0)
    if tech_count == 0:
        weak_skill_areas.append('No technical skills were detected on this resume')
    elif tech_count < 8:
        weak_skill_areas.append(f'Limited technical skills detected ({tech_count})')
    if soft_count == 0:
        weak_skill_areas.append('No soft skills were detected')

    missing_sections_detail = []
    if not extracted.get('education') or 'education' in (formatting_result.get('sections_missing') or []):
        missing_sections_detail.append('Education')
    if not extracted.get('experience') or 'experience' in (formatting_result.get('sections_missing') or []):
        missing_sections_detail.append('Experience')
    if not (extracted.get('skills') or {}).get('technical') or 'skills' in (formatting_result.get('sections_missing') or []):
        missing_sections_detail.append('Skills')
    if not extracted.get('projects') or 'projects' in (formatting_result.get('sections_missing') or []):
        missing_sections_detail.append('Projects')
    if not extracted.get('summary'):
        missing_sections_detail.append('Professional Summary')
    if not extracted.get('certifications'):
        missing_sections_detail.append('Certifications')
    # Deduplicate while preserving order
    seen = set()
    unique_sections = []
    for sec in missing_sections_detail:
        if sec not in seen:
            seen.add(sec)
            unique_sections.append(sec)

    other_gaps = []
    if not extracted.get('email'):
        other_gaps.append('Email address not detected — ATS parsers often require contact fields')
    if not extracted.get('phone'):
        other_gaps.append('Phone number not detected')
    if not extracted.get('linkedin'):
        other_gaps.append('LinkedIn URL not detected')
    if (extracted.get('measurable_achievements_count') or 0) < 2:
        other_gaps.append('Few or no quantified achievements (numbers, percentages, or metrics)')
    if len(keyword_result.get('action_verbs') or []) < 4:
        other_gaps.append('Few strong action verbs detected in experience bullets')
    word_count = keyword_result.get('word_count') or 0
    if word_count and word_count < 200:
        other_gaps.append(f'Resume text is short ({word_count} words), which can reduce ATS keyword coverage')

    return {
        'missing_keywords_general': missing_keywords_general[:12],
        'weak_skill_areas': weak_skill_areas,
        'missing_sections_detail': unique_sections,
        'other_gaps': other_gaps,
    }


def enrich_ats_display(extracted: dict, raw_text: str, ats_data: dict) -> dict:
    """Fill newer display fields for older analysis JSON records."""
    ats_data = dict(ats_data or {})
    extracted = extracted or {}
    if not ats_data:
        return ats_data

    if ats_data.get('professional_strength_score') is None:
        ats_data['professional_strength_score'] = compute_professional_strength(
            ats_data.get('skills_score', 0),
            ats_data.get('experience_score', 0),
            ats_data.get('projects_score', 0),
            extracted.get('measurable_achievements_count', ats_data.get('measurable_achievements', 0)),
            len(ats_data.get('action_verbs') or []),
        )

    factual = detect_factual_strengths(extracted)
    if factual:
        ats_data['strengths'] = factual

    if ats_data.get('missing_keywords_general') is None:
        keyword_result = {
            'keywords_found': ats_data.get('keywords_found') or [],
            'action_verbs': ats_data.get('action_verbs') or [],
            'word_count': ats_data.get('word_count') or len((raw_text or '').split()),
        }
        formatting_result = {
            'sections_missing': ats_data.get('sections_missing') or [],
        }
        skills = extracted.get('skills') or {}
        skills_result = {
            'tech_count': len(skills.get('technical') or []),
            'soft_count': len(skills.get('soft') or []),
        }
        gaps = collect_ats_gaps(extracted, raw_text, keyword_result, formatting_result, skills_result)
        ats_data['missing_keywords_general'] = gaps['missing_keywords_general']
        ats_data['weak_skill_areas'] = gaps['weak_skill_areas']
        ats_data['missing_sections_detail'] = gaps['missing_sections_detail']
        ats_data['ats_gaps'] = gaps['other_gaps']

    word_count = ats_data.get('word_count') or len((raw_text or '').split())
    ats_data['word_count'] = word_count
    if ats_data.get('incomplete') is None:
        ats_data['incomplete'] = word_count < 40
        ats_data['incomplete_reason'] = (
            'Very little text could be extracted from this PDF. It may be image-based or poorly encoded. '
            'Only fields and metrics that were actually detected are shown.'
            if ats_data['incomplete'] else ''
        )
    return ats_data
