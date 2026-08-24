"""
Resume Parser Service
Extracts structured information from PDF resumes using NLP.
"""
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Try importing heavy deps, fall back gracefully ──────────────────────────

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import spacy
    try:
        nlp = spacy.load('en_core_web_sm')
        HAS_SPACY = True
    except OSError:
        HAS_SPACY = False
        nlp = None
except ImportError:
    HAS_SPACY = False
    nlp = None

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except Exception:
            pass
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        try:
            nltk.download('stopwords', quiet=True)
        except Exception:
            pass
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
        except Exception:
            pass
    HAS_NLTK = True
    try:
        STOP_WORDS = set(stopwords.words('english'))
    except Exception:
        STOP_WORDS = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are'}
except Exception:
    HAS_NLTK = False
    STOP_WORDS = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are'}


# ── Keyword lists ─────────────────────────────────────────────────────────

TECH_SKILLS = {
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'ruby',
    'php', 'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab', 'perl',
    'bash', 'shell', 'powershell', 'sql', 'nosql', 'html', 'css', 'xml',
    'json', 'yaml', 'react', 'angular', 'vue', 'node.js', 'nodejs', 'express',
    'django', 'flask', 'fastapi', 'spring', 'hibernate', 'laravel', 'rails',
    'asp.net', 'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 'opencv', 'nltk',
    'spacy', 'huggingface', 'transformers', 'langchain', 'openai', 'llm',
    'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra', 'oracle',
    'dynamodb', 'firebase', 'elasticsearch', 'hadoop', 'spark', 'kafka',
    'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab', 'bitbucket',
    'aws', 'azure', 'gcp', 'heroku', 'netlify', 'vercel', 'linux', 'ubuntu',
    'windows', 'macos', 'rest', 'restful', 'api', 'graphql', 'grpc', 'soap',
    'microservices', 'serverless', 'ci/cd', 'devops', 'agile', 'scrum', 'jira',
    'tableau', 'power bi', 'excel', 'figma', 'adobe xd', 'postman', 'swagger',
    'selenium', 'pytest', 'junit', 'jest', 'mocha', 'webpack', 'vite',
    'machine learning', 'deep learning', 'nlp', 'computer vision', 'data science',
    'data analysis', 'data engineering', 'blockchain', 'android', 'ios', 'flutter',
    'react native', 'unity', 'unreal', 'opengl', 'vulkan',
}

SOFT_SKILLS = {
    'communication', 'teamwork', 'leadership', 'problem solving', 'creativity',
    'adaptability', 'time management', 'critical thinking', 'analytical',
    'collaboration', 'project management', 'presentation', 'negotiation',
    'conflict resolution', 'decision making', 'multitasking', 'attention to detail',
    'customer service', 'mentoring', 'coaching',
}

EDUCATION_KEYWORDS = [
    'bachelor', 'master', 'phd', 'doctorate', 'associate', 'diploma',
    'b.tech', 'b.e', 'm.tech', 'm.e', 'b.sc', 'm.sc', 'mba', 'bba',
    'b.com', 'm.com', 'be', 'me', 'btech', 'mtech', 'bsc', 'msc',
    'engineering', 'computer science', 'information technology', 'software',
    'electrical', 'mechanical', 'civil', 'electronics', 'data science',
    'artificial intelligence', 'machine learning', 'university', 'college',
    'institute', 'school', 'cgpa', 'gpa', 'percentage', 'grade',
]

EXPERIENCE_KEYWORDS = [
    'experience', 'work', 'employment', 'internship', 'intern', 'job',
    'position', 'role', 'responsibility', 'responsibilities', 'worked',
    'developed', 'implemented', 'managed', 'led', 'designed', 'built',
    'created', 'maintained', 'collaborated', 'achieved',
]

CERT_KEYWORDS = [
    'certified', 'certification', 'certificate', 'aws certified', 'google certified',
    'microsoft certified', 'oracle certified', 'cisco certified', 'pmp', 'scrum',
    'coursera', 'udemy', 'edx', 'linkedin learning', 'nptel', 'ibm',
]

SECTION_HEADERS = {
    'skills': ['skills', 'technical skills', 'core competencies', 'expertise',
               'technologies', 'tools', 'tech stack', 'programming languages'],
    'education': ['education', 'academic background', 'qualifications', 'academic details',
                  'educational background'],
    'experience': ['experience', 'work experience', 'professional experience',
                   'employment history', 'work history', 'career history'],
    'projects': ['projects', 'personal projects', 'academic projects', 'key projects',
                 'project work', 'portfolio'],
    'certifications': ['certifications', 'certificates', 'professional certifications',
                       'courses', 'training'],
    'summary': ['summary', 'objective', 'professional summary', 'career objective',
                'about', 'profile', 'introduction'],
    'achievements': ['achievements', 'accomplishments', 'awards', 'honors', 'recognition'],
    'languages': ['languages', 'language skills'],
}


# ── Core extraction functions ─────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file."""
    text = ''
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    # Try pdfplumber first (better layout preservation)
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

    # Fallback to PyPDF2
    if HAS_PYPDF2:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")

    if not text.strip():
        raise ValueError("Could not extract text from PDF. The file may be image-based or corrupted.")
    return text


def extract_name(text: str, lines: list) -> str:
    """Try to extract candidate name from resume text."""
    # spaCy NER
    if HAS_SPACY and nlp:
        try:
            doc = nlp(text[:500])
            for ent in doc.ents:
                if ent.label_ == 'PERSON' and len(ent.text.split()) >= 2:
                    return ent.text.strip()
        except Exception:
            pass

    # Heuristic: first non-empty line that isn't an email/phone/url
    for line in lines[:10]:
        line = line.strip()
        if not line:
            continue
        if re.search(r'[@\d\+\-\(\)http://www]', line.split()[0] if line.split() else ''):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w.isalpha()):
            return line
    return ''


def extract_email(text: str) -> str:
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else ''


def extract_phone(text: str) -> str:
    patterns = [
        r'(\+91[\s\-]?)?[789]\d{9}',
        r'(\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}',
        r'\d{10}',
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(0).strip()
    return ''


def extract_location(text: str) -> str:
    # Look for common location patterns
    patterns = [
        r'(?:Location|Address|City)[:\s]+([A-Za-z\s,]+?)(?:\n|$)',
        r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*(?:,\s*[A-Z]{2})?)\s*(?:\d{6}|\d{5})?',
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            loc = match.group(1).strip()
            if 3 < len(loc) < 60:
                return loc
    return ''


def extract_linkedin(text: str) -> str:
    match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
    return f"https://{match.group(0)}" if match else ''


def extract_github(text: str) -> str:
    match = re.search(r'github\.com/[\w\-]+', text, re.IGNORECASE)
    return f"https://{match.group(0)}" if match else ''


def extract_skills(text: str, lines: list) -> dict:
    """Extract technical and soft skills from resume text."""
    text_lower = text.lower()
    tech = []
    soft = []

    for skill in TECH_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            tech.append(skill.title() if len(skill) <= 4 else skill.capitalize())

    for skill in SOFT_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            soft.append(skill.title())

    # Also parse skills section specifically
    in_skills = False
    for line in lines:
        line_lower = line.strip().lower()
        if any(h == line_lower for h in SECTION_HEADERS['skills']):
            in_skills = True
            continue
        if in_skills:
            if any(h == line_lower for section in SECTION_HEADERS.values()
                   for h in section if line_lower not in SECTION_HEADERS['skills']):
                in_skills = False
                continue
            # Parse comma/bullet separated skills
            parts = re.split(r'[,|•\n]+', line)
            for part in parts:
                part = part.strip()
                if 1 < len(part) < 40 and part not in tech:
                    tech.append(part)

    # Deduplicate while preserving order
    seen = set()
    unique_tech = []
    for s in tech:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_tech.append(s)

    return {'technical': unique_tech[:40], 'soft': list(set(soft))[:20]}


def extract_education(text: str, lines: list) -> list:
    """Extract education entries."""
    education = []
    in_edu = False
    current_entry = []

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        if any(h in line_lower for h in SECTION_HEADERS['education']) and len(line_stripped) < 40:
            in_edu = True
            continue
        elif in_edu and any(h in line_lower for section_key, headers in SECTION_HEADERS.items()
                            for h in headers if section_key != 'education') and len(line_stripped) < 40:
            if current_entry:
                education.append(' '.join(current_entry))
                current_entry = []
            in_edu = False
            continue

        if in_edu and line_stripped:
            current_entry.append(line_stripped)
            if len(current_entry) >= 3:
                education.append(' '.join(current_entry))
                current_entry = []

    if current_entry:
        education.append(' '.join(current_entry))

    # Also search the entire text for degree patterns
    if not education:
        degree_pattern = r'(?:B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|MBA|BBA|B\.?Com|M\.?Com|Ph\.?D|Bachelor|Master|Diploma)[^\n]{5,80}'
        matches = re.findall(degree_pattern, text, re.IGNORECASE)
        education = [m.strip() for m in matches[:5]]

    return education[:5]


def extract_experience(text: str, lines: list) -> list:
    """Extract work/internship experience entries."""
    experience = []
    in_exp = False
    current = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if any(h in lower for h in SECTION_HEADERS['experience']) and len(stripped) < 40:
            in_exp = True
            current = []
            continue
        elif in_exp and any(h in lower for section_key, headers in SECTION_HEADERS.items()
                            for h in headers if section_key != 'experience') and len(stripped) < 40:
            if current:
                experience.append(' | '.join(current))
                current = []
            in_exp = False
            continue

        if in_exp and stripped:
            current.append(stripped)
            # New entry heuristic: line with year pattern
            if re.search(r'\b(20\d{2}|19\d{2})\b', stripped) and current:
                if len(current) > 1:
                    experience.append(' | '.join(current[:-1]))
                    current = [stripped]

    if current:
        experience.append(' | '.join(current))

    return experience[:8]


def extract_projects(text: str, lines: list) -> list:
    """Extract project entries."""
    projects = []
    in_proj = False
    current = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if any(h in lower for h in SECTION_HEADERS['projects']) and len(stripped) < 40:
            in_proj = True
            current = []
            continue
        elif in_proj and any(h in lower for section_key, headers in SECTION_HEADERS.items()
                             for h in headers if section_key != 'projects') and len(stripped) < 40:
            if current:
                projects.append(' '.join(current))
                current = []
            in_proj = False
            continue

        if in_proj and stripped:
            current.append(stripped)
            if len(current) >= 4:
                projects.append(' '.join(current))
                current = []

    if current:
        projects.append(' '.join(current))

    return projects[:6]


def extract_certifications(text: str) -> list:
    """Extract certifications."""
    certs = []
    for line in text.split('\n'):
        line = line.strip()
        if any(kw in line.lower() for kw in CERT_KEYWORDS) and 5 < len(line) < 200:
            certs.append(line)
    return list(dict.fromkeys(certs))[:10]


def extract_languages(text: str) -> list:
    """Extract spoken languages."""
    common_langs = [
        'english', 'hindi', 'spanish', 'french', 'german', 'arabic', 'chinese',
        'japanese', 'portuguese', 'russian', 'korean', 'italian', 'bengali',
        'telugu', 'marathi', 'tamil', 'gujarati', 'urdu', 'kannada', 'malayalam',
        'punjabi', 'odia',
    ]
    text_lower = text.lower()
    found = []
    in_lang_section = False

    for line in text.split('\n'):
        lower = line.strip().lower()
        if any(h == lower for h in SECTION_HEADERS['languages']):
            in_lang_section = True
            continue
        if in_lang_section:
            for lang in common_langs:
                if lang in lower and lang.capitalize() not in found:
                    found.append(lang.capitalize())
            if len(lower) < 3 or any(
                any(h == lower for h in headers)
                for headers in SECTION_HEADERS.values()
            ):
                in_lang_section = False

    if not found:
        for lang in common_langs:
            if re.search(r'\b' + lang + r'\b', text_lower):
                found.append(lang.capitalize())

    return found[:8]


def extract_summary(text: str, lines: list) -> str:
    """Extract professional summary."""
    in_summary = False
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if any(h in lower for h in SECTION_HEADERS['summary']) and len(stripped) < 40:
            in_summary = True
            continue
        elif in_summary and any(h in lower for section_key, headers in SECTION_HEADERS.items()
                                for h in headers if section_key != 'summary') and len(stripped) < 40:
            break

        if in_summary and stripped:
            summary_lines.append(stripped)
            if len(summary_lines) >= 5:
                break

    return ' '.join(summary_lines)


def extract_achievements(text: str) -> list:
    """Extract achievements."""
    achievements = []
    in_ach = False

    for line in text.split('\n'):
        stripped = line.strip()
        lower = stripped.lower()
        if any(h in lower for h in SECTION_HEADERS['achievements']) and len(stripped) < 40:
            in_ach = True
            continue
        elif in_ach and any(h in lower for section_key, headers in SECTION_HEADERS.items()
                            for h in headers if section_key != 'achievements') and len(stripped) < 40:
            in_ach = False
            continue
        if in_ach and stripped and len(stripped) > 10:
            achievements.append(stripped)

    return achievements[:8]


def count_action_verbs(text: str) -> list:
    """Count strong action verbs used in resume."""
    action_verbs = [
        'developed', 'implemented', 'designed', 'built', 'created', 'managed',
        'led', 'spearheaded', 'launched', 'delivered', 'achieved', 'improved',
        'increased', 'reduced', 'optimized', 'automated', 'collaborated',
        'coordinated', 'analyzed', 'researched', 'engineered', 'deployed',
        'integrated', 'maintained', 'supervised', 'mentored', 'trained',
        'resolved', 'streamlined', 'generated', 'established', 'oversaw',
        'transformed', 'accelerated', 'drove', 'pioneered', 'revolutionized',
    ]
    text_lower = text.lower()
    found = [v for v in action_verbs if re.search(r'\b' + v + r'\b', text_lower)]
    return found


def count_measurable_achievements(text: str) -> int:
    """Count lines with measurable achievements (%, numbers)."""
    pattern = r'\d+\s*(?:%|percent|x|times|million|billion|thousand|k\b|lakh|crore)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return len(matches)


# ── Main parse function ───────────────────────────────────────────────────

def parse_resume(file_path: str) -> dict:
    """
    Main entry point: parse a PDF resume and return structured data.
    Returns a dict with all extracted fields.
    """
    try:
        raw_text = extract_text_from_pdf(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {e}")

    lines = [l for l in raw_text.split('\n') if l.strip()]

    name = extract_name(raw_text, lines)
    email = extract_email(raw_text)
    phone = extract_phone(raw_text)
    location = extract_location(raw_text)
    linkedin = extract_linkedin(raw_text)
    github = extract_github(raw_text)
    skills = extract_skills(raw_text, lines)
    education = extract_education(raw_text, lines)
    experience = extract_experience(raw_text, lines)
    projects = extract_projects(raw_text, lines)
    certifications = extract_certifications(raw_text)
    languages = extract_languages(raw_text)
    summary = extract_summary(raw_text, lines)
    achievements = extract_achievements(raw_text)
    action_verbs = count_action_verbs(raw_text)
    measurable_count = count_measurable_achievements(raw_text)

    word_count = len(raw_text.split())
    char_count = len(raw_text)

    return {
        'name': name,
        'email': email,
        'phone': phone,
        'location': location,
        'linkedin': linkedin,
        'github': github,
        'summary': summary,
        'skills': skills,
        'education': education,
        'experience': experience,
        'projects': projects,
        'certifications': certifications,
        'languages': languages,
        'achievements': achievements,
        'action_verbs': action_verbs,
        'measurable_achievements_count': measurable_count,
        'word_count': word_count,
        'char_count': char_count,
        'raw_text': raw_text,
    }
