"""
Job Matcher Service
Compares resume content against a job description using TF-IDF cosine similarity
and skill gap analysis.
"""
import re
import logging
import math

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    try:
        STOP_WORDS = set(stopwords.words('english'))
    except Exception:
        try:
            nltk.download('stopwords', quiet=True)
            STOP_WORDS = set(stopwords.words('english'))
        except Exception:
            STOP_WORDS = {
                'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'shall', 'can', 'not', 'no', 'nor', 'so',
            }
    HAS_NLTK = True
except Exception:
    HAS_NLTK = False
    STOP_WORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'not', 'no', 'nor', 'so',
    }



def clean_text(text: str) -> str:
    """Clean text for comparison."""
    if not text:
        return ''
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_jd_keywords(jd_text: str) -> list:
    """Extract key terms from job description."""
    jd_clean = clean_text(jd_text)
    words = jd_clean.split()
    # Remove stop words and short words
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    # Count frequency
    freq = {}
    for w in meaningful:
        freq[w] = freq.get(w, 0) + 1
    # Return sorted by frequency
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, c in sorted_words[:40]]


def compute_tfidf_similarity(resume_text: str, jd_text: str) -> float:
    """Compute cosine similarity using TF-IDF."""
    if not HAS_SKLEARN:
        return _fallback_similarity(resume_text, jd_text)

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_features=5000,
        )
        vectors = vectorizer.fit_transform([clean_text(resume_text), clean_text(jd_text)])
        sim = cosine_similarity(vectors[0], vectors[1])[0][0]
        return round(float(sim) * 100, 2)
    except Exception as e:
        logger.warning(f"TF-IDF failed: {e}, using fallback")
        return _fallback_similarity(resume_text, jd_text)


def _fallback_similarity(text1: str, text2: str) -> float:
    """Simple Jaccard similarity fallback."""
    words1 = set(clean_text(text1).split()) - STOP_WORDS
    words2 = set(clean_text(text2).split()) - STOP_WORDS
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return round(len(intersection) / len(union) * 100, 2)


def find_matching_skills(resume_skills: list, jd_text: str) -> list:
    """Find skills from resume that appear in JD."""
    jd_lower = jd_text.lower()
    matching = []
    for skill in resume_skills:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', jd_lower):
            matching.append(skill)
    return matching


def find_missing_skills(resume_skills: list, jd_text: str, jd_keywords: list) -> list:
    """Find skills mentioned in JD that are missing from resume."""
    resume_lower = {s.lower() for s in resume_skills}
    missing = []

    # Common tech skills to check in JD
    tech_vocab = [
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'node', 'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'docker', 'kubernetes',
        'aws', 'azure', 'gcp', 'git', 'github', 'ci/cd', 'devops', 'linux',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras',
        'scikit-learn', 'data analysis', 'tableau', 'power bi', 'excel',
        'html', 'css', 'rest', 'api', 'graphql', 'microservices', 'agile',
        'scrum', 'jira', 'jenkins', 'ansible', 'terraform', 'spark', 'hadoop',
        'kafka', 'elasticsearch', 'flutter', 'android', 'ios', 'swift', 'kotlin',
        'c++', 'c#', 'go', 'rust', 'scala', 'r', 'matlab', 'nlp', 'opencv',
    ]

    jd_lower = jd_text.lower()
    for tech in tech_vocab:
        if re.search(r'\b' + re.escape(tech) + r'\b', jd_lower):
            if tech not in resume_lower:
                missing.append(tech.capitalize() if len(tech) > 3 else tech.upper())

    # Also check JD keywords
    for kw in jd_keywords[:20]:
        if len(kw) > 3 and kw not in resume_lower and kw not in [m.lower() for m in missing]:
            missing.append(kw.capitalize())

    return list(dict.fromkeys(missing))[:15]


def detect_job_role_match(jd_text: str, extracted: dict) -> dict:
    """Detect if the resume matches the job role domain."""
    jd_lower = jd_text.lower()
    resume_skills_lower = {s.lower() for s in extracted.get('skills', {}).get('technical', [])}

    # Domain detection
    domains = {
        'Software Development': ['software', 'developer', 'programmer', 'coding', 'full stack', 'backend', 'frontend'],
        'Data Science / ML': ['data scientist', 'machine learning', 'deep learning', 'ai', 'ml engineer', 'data engineer'],
        'DevOps / Cloud': ['devops', 'cloud', 'aws', 'azure', 'kubernetes', 'docker', 'infrastructure'],
        'Cybersecurity': ['security', 'penetration', 'ethical hacking', 'cybersecurity', 'soc', 'siem'],
        'Mobile Development': ['android', 'ios', 'mobile', 'flutter', 'react native', 'swift', 'kotlin'],
        'Data Analysis': ['data analyst', 'business analyst', 'tableau', 'power bi', 'excel', 'sql'],
        'Web Development': ['web developer', 'html', 'css', 'react', 'angular', 'vue', 'frontend'],
        'QA / Testing': ['qa', 'quality assurance', 'testing', 'selenium', 'automation', 'test engineer'],
        'Product / Management': ['product manager', 'scrum', 'agile', 'project manager', 'pmp'],
    }

    jd_domain = None
    for domain, keywords in domains.items():
        if any(kw in jd_lower for kw in keywords):
            jd_domain = domain
            break

    # Check if resume domain aligns
    resume_domain_score = 50  # neutral default
    if jd_domain:
        domain_keywords = domains.get(jd_domain, [])
        matches = sum(1 for kw in domain_keywords if kw in resume_skills_lower)
        resume_domain_score = min(100, matches * 20 + 20)

    return {
        'jd_domain': jd_domain or 'General',
        'role_match_score': resume_domain_score,
        'role_matched': resume_domain_score >= 40,
    }


def check_education_match(jd_text: str, extracted: dict) -> dict:
    """Check if education matches JD requirements."""
    jd_lower = jd_text.lower()
    education = extracted.get('education', [])
    edu_text = ' '.join(education).lower()

    issues = []
    score = 70  # Default decent score

    # Check degree requirements
    if 'bachelor' in jd_lower or "b.tech" in jd_lower or "degree" in jd_lower:
        if any(k in edu_text for k in ['bachelor', 'b.tech', 'be', 'btech', 'b.e']):
            score = 90
        elif not education:
            score = 30
            issues.append('No education information found in resume.')
        else:
            score = 60

    if 'master' in jd_lower or "m.tech" in jd_lower or "msc" in jd_lower:
        if any(k in edu_text for k in ['master', 'm.tech', 'mtech', 'msc', 'm.sc']):
            score = 95
        else:
            score = 55
            issues.append('Job may prefer Master\'s degree — consider highlighting equivalent experience.')

    return {
        'score': round(score, 1),
        'issues': issues,
    }


def check_experience_match(jd_text: str, extracted: dict) -> dict:
    """Check experience level match."""
    jd_lower = jd_text.lower()
    experience = extracted.get('experience', [])
    exp_count = len(experience)

    issues = []
    score = 60

    # Detect required years
    years_match = re.search(r'(\d+)[\+]?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', jd_lower)
    required_years = int(years_match.group(1)) if years_match else None

    if 'fresher' in jd_lower or 'entry level' in jd_lower or '0 year' in jd_lower:
        score = 85
    elif required_years is not None:
        if exp_count == 0:
            score = 30
            issues.append(f'Job requires {required_years}+ years of experience — add any relevant experience.')
        elif exp_count >= required_years:
            score = 90
        else:
            score = max(40, 90 - (required_years - exp_count) * 15)
            if required_years > exp_count:
                issues.append(f'Job expects ~{required_years} years of experience.')
    elif exp_count == 0:
        if 'internship' in jd_lower:
            score = 60
        else:
            score = 40
            issues.append('No experience entries found — add internships or relevant work.')
    else:
        score = min(90, 50 + exp_count * 15)

    return {
        'score': round(score, 1),
        'required_years': required_years,
        'found_entries': exp_count,
        'issues': issues,
    }


def match_resume_to_job(extracted: dict, raw_text: str, jd_text: str,
                        job_title: str = '', company: str = '') -> dict:
    """
    Main job matching function.
    Returns comprehensive match analysis.
    """
    if not jd_text or not raw_text:
        return {'error': 'Missing resume or job description text.'}

    resume_skills = (
        extracted.get('skills', {}).get('technical', []) +
        extracted.get('skills', {}).get('soft', [])
    )

    # Core similarity
    text_similarity = compute_tfidf_similarity(raw_text, jd_text)

    # Extract JD keywords
    jd_keywords = extract_jd_keywords(jd_text)

    # Skill matching
    matching_skills = find_matching_skills(resume_skills, jd_text)
    missing_skills = find_missing_skills(resume_skills, jd_text, jd_keywords)

    # Domain/role match
    role_analysis = detect_job_role_match(jd_text, extracted)

    # Education match
    edu_match = check_education_match(jd_text, extracted)

    # Experience match
    exp_match = check_experience_match(jd_text, extracted)

    # Keyword overlap
    jd_kw_set = set(jd_keywords)
    resume_words = set(clean_text(raw_text).split())
    kw_overlap = jd_kw_set & resume_words
    keyword_match_pct = round(len(kw_overlap) / max(len(jd_kw_set), 1) * 100, 1)

    # Project match (do projects mention JD keywords?)
    projects = extracted.get('projects', [])
    projects_text = ' '.join(projects).lower()
    project_relevance = sum(1 for kw in jd_keywords[:15] if kw in projects_text)
    project_score = min(100, project_relevance * 15 + 20)

    # Cert match
    certs = extracted.get('certifications', [])
    cert_text = ' '.join(certs).lower()
    cert_relevance = sum(1 for kw in jd_keywords[:10] if kw in cert_text)
    cert_score = min(100, cert_relevance * 20 + 30) if certs else 20

    # Skill match percentage
    if resume_skills:
        skill_match_pct = round(len(matching_skills) / max(len(resume_skills), 1) * 100, 1)
    else:
        skill_match_pct = 0

    # Weighted overall match
    overall_match = (
        text_similarity * 0.25 +
        skill_match_pct * 0.25 +
        keyword_match_pct * 0.15 +
        role_analysis['role_match_score'] * 0.10 +
        edu_match['score'] * 0.10 +
        exp_match['score'] * 0.08 +
        project_score * 0.04 +
        cert_score * 0.03
    )
    overall_match = round(min(100, max(0, overall_match)), 1)

    # Decision
    if overall_match >= 70:
        decision = 'RECOMMENDED'
        decision_label = '✓ RECOMMENDED'
        decision_color = 'success'
    elif overall_match >= 55:
        decision = 'CONDITIONALLY_RECOMMENDED'
        decision_label = '⚠ CONDITIONALLY RECOMMENDED'
        decision_color = 'warning'
    else:
        decision = 'NOT_RECOMMENDED'
        decision_label = '❌ NOT RECOMMENDED'
        decision_color = 'danger'

    # Job readiness score (rounded friendly number)
    job_readiness = round((overall_match + skill_match_pct) / 2, 1)

    return {
        'overall_match': overall_match,
        'text_similarity': round(text_similarity, 1),
        'skill_match_pct': skill_match_pct,
        'keyword_match_pct': keyword_match_pct,
        'matching_skills': matching_skills[:20],
        'missing_skills': missing_skills[:15],
        'jd_keywords': jd_keywords[:20],
        'keywords_found': list(kw_overlap)[:20],
        'role_analysis': role_analysis,
        'education_match': edu_match,
        'experience_match': exp_match,
        'project_score': project_score,
        'cert_score': cert_score,
        'job_readiness': job_readiness,
        'decision': decision,
        'decision_label': decision_label,
        'decision_color': decision_color,
        'job_title': job_title,
        'company': company,
        'skill_gap': len(missing_skills),
        'strengths': _compile_strengths(matching_skills, role_analysis, edu_match, exp_match),
        'weaknesses': _compile_weaknesses(missing_skills, role_analysis, edu_match, exp_match, overall_match),
    }


def _compile_strengths(matching_skills, role_analysis, edu_match, exp_match):
    strengths = []
    if matching_skills:
        strengths.append(f'{len(matching_skills)} matching skills found: {", ".join(matching_skills[:5])}.')
    if role_analysis['role_matched']:
        strengths.append(f'Resume aligns with {role_analysis["jd_domain"]} domain.')
    if edu_match['score'] >= 75:
        strengths.append('Education background matches job requirements.')
    if exp_match['score'] >= 70:
        strengths.append('Experience level is appropriate for this role.')
    return strengths


def _compile_weaknesses(missing_skills, role_analysis, edu_match, exp_match, overall):
    weaknesses = []
    if missing_skills:
        weaknesses.append(f'Missing {len(missing_skills)} skills required by the job.')
    if not role_analysis['role_matched']:
        weaknesses.append(f'Resume may not align well with {role_analysis["jd_domain"]} requirements.')
    if edu_match['score'] < 60:
        for issue in edu_match.get('issues', []):
            weaknesses.append(issue)
    if exp_match['score'] < 60:
        for issue in exp_match.get('issues', []):
            weaknesses.append(issue)
    if overall < 50:
        weaknesses.append('Low overall keyword alignment with job description.')
    return weaknesses
