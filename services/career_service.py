"""
Career Service
Provides career roadmap, skill recommendations, interview prep, and learning resources
based on resume and target role.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Role-specific career data ─────────────────────────────────────────────

CAREER_DATA = {
    'software developer': {
        'skills_to_learn': ['System Design', 'Data Structures & Algorithms', 'REST APIs',
                            'Docker & Kubernetes', 'CI/CD Pipelines', 'Cloud (AWS/Azure/GCP)'],
        'certifications': ['AWS Solutions Architect', 'Google Professional Developer',
                           'Microsoft Azure Developer', 'Docker Certified Associate'],
        'project_ideas': [
            'Build a full-stack web app with React + Node.js + PostgreSQL',
            'Create a microservices architecture with Docker and Kubernetes',
            'Develop a REST API with authentication (JWT/OAuth)',
            'Build a real-time chat application using WebSockets',
            'Create a CI/CD pipeline using GitHub Actions',
        ],
        'interview_topics': [
            'OOP principles and SOLID design patterns',
            'Time and space complexity (Big O)',
            'Common data structures: arrays, linked lists, trees, graphs',
            'Database design and SQL optimization',
            'System design: load balancing, caching, scaling',
            'Git workflow and code review practices',
        ],
        'roadmap': [
            {'phase': 'Foundation', 'duration': '1–2 months',
             'tasks': ['Strengthen DSA', 'Build 2 portfolio projects', 'Learn version control']},
            {'phase': 'Intermediate', 'duration': '2–3 months',
             'tasks': ['Learn system design basics', 'Master one cloud platform', 'Get certified']},
            {'phase': 'Job Ready', 'duration': '1–2 months',
             'tasks': ['Mock interviews', 'Apply to 20+ companies', 'Network on LinkedIn']},
        ],
        'learning_resources': [
            {'name': 'LeetCode', 'type': 'Practice', 'url': 'https://leetcode.com'},
            {'name': 'System Design Primer', 'type': 'Free', 'url': 'https://github.com/donnemartin/system-design-primer'},
            {'name': 'CS50', 'type': 'Free', 'url': 'https://cs50.harvard.edu'},
            {'name': 'freeCodeCamp', 'type': 'Free', 'url': 'https://freecodecamp.org'},
        ],
    },
    'data scientist': {
        'skills_to_learn': ['Statistics & Probability', 'Machine Learning', 'Deep Learning',
                            'Feature Engineering', 'MLOps', 'SQL', 'Data Visualization'],
        'certifications': ['Google Professional Data Engineer', 'IBM Data Science',
                           'TensorFlow Developer Certificate', 'AWS Machine Learning Specialty'],
        'project_ideas': [
            'Build an end-to-end ML pipeline (data → model → API)',
            'Create a sentiment analysis tool with BERT/transformers',
            'Develop a recommendation system (collaborative filtering)',
            'Build a computer vision app (object detection / classification)',
            'Create a time-series forecasting model for stock/sales data',
        ],
        'interview_topics': [
            'Bias-variance tradeoff and overfitting/underfitting',
            'Supervised vs unsupervised learning',
            'Evaluation metrics: precision, recall, F1, AUC-ROC',
            'Feature engineering and selection techniques',
            'SQL for data manipulation',
            'Python (Pandas, NumPy, Matplotlib)',
        ],
        'roadmap': [
            {'phase': 'Statistics & Python', 'duration': '1–2 months',
             'tasks': ['Learn statistics', 'Master Pandas/NumPy', 'Data visualization']},
            {'phase': 'ML & Projects', 'duration': '2–3 months',
             'tasks': ['Complete 3 ML projects', 'Kaggle competitions', 'Learn SQL']},
            {'phase': 'Job Ready', 'duration': '1–2 months',
             'tasks': ['Build portfolio', 'Mock interviews', 'Apply to companies']},
        ],
        'learning_resources': [
            {'name': 'Kaggle', 'type': 'Free', 'url': 'https://kaggle.com'},
            {'name': 'fast.ai', 'type': 'Free', 'url': 'https://fast.ai'},
            {'name': 'StatQuest', 'type': 'Free', 'url': 'https://statquest.org'},
            {'name': 'Google ML Crash Course', 'type': 'Free', 'url': 'https://developers.google.com/machine-learning/crash-course'},
        ],
    },
    'web developer': {
        'skills_to_learn': ['JavaScript ES6+', 'React/Vue/Angular', 'Node.js', 'TypeScript',
                            'CSS Frameworks', 'Web Performance', 'Accessibility'],
        'certifications': ['Meta Frontend Developer', 'Google Web Fundamentals',
                           'MongoDB Developer', 'freeCodeCamp'],
        'project_ideas': [
            'Build a responsive e-commerce site with React and a backend API',
            'Create a real-time dashboard with WebSockets',
            'Develop a Progressive Web App (PWA)',
            'Build a social media clone (authentication, posts, comments)',
            'Create a portfolio website with animations',
        ],
        'interview_topics': [
            'JavaScript fundamentals: closures, promises, async/await',
            'React hooks: useState, useEffect, custom hooks',
            'CSS: Flexbox, Grid, responsive design',
            'Browser performance optimization',
            'REST API design and integration',
            'Cross-browser compatibility',
        ],
        'roadmap': [
            {'phase': 'Frontend Basics', 'duration': '1–2 months',
             'tasks': ['HTML/CSS/JS mastery', 'Build 2 static websites', 'Learn Git']},
            {'phase': 'Framework & Backend', 'duration': '2–3 months',
             'tasks': ['React or Vue', 'Node.js + Express', 'Database basics']},
            {'phase': 'Job Ready', 'duration': '1–2 months',
             'tasks': ['Deploy projects', 'Open source contributions', 'Job applications']},
        ],
        'learning_resources': [
            {'name': 'MDN Web Docs', 'type': 'Free', 'url': 'https://developer.mozilla.org'},
            {'name': 'The Odin Project', 'type': 'Free', 'url': 'https://theodinproject.com'},
            {'name': 'javascript.info', 'type': 'Free', 'url': 'https://javascript.info'},
            {'name': 'CSS Tricks', 'type': 'Free', 'url': 'https://css-tricks.com'},
        ],
    },
    'devops engineer': {
        'skills_to_learn': ['Docker', 'Kubernetes', 'Terraform', 'CI/CD', 'Cloud Platforms',
                            'Monitoring (Prometheus/Grafana)', 'Linux Administration'],
        'certifications': ['AWS DevOps Engineer', 'CKA (Certified Kubernetes Administrator)',
                           'HashiCorp Terraform', 'Google Professional DevOps Engineer'],
        'project_ideas': [
            'Set up a Kubernetes cluster and deploy a multi-container app',
            'Build a CI/CD pipeline with Jenkins/GitHub Actions',
            'Create infrastructure-as-code with Terraform',
            'Set up monitoring and alerting with Prometheus + Grafana',
            'Automate server provisioning with Ansible',
        ],
        'interview_topics': [
            'Docker: containers, images, docker-compose',
            'Kubernetes: pods, deployments, services, ingress',
            'CI/CD pipeline design and best practices',
            'Cloud architecture (VPC, IAM, S3, EC2)',
            'Linux commands and shell scripting',
            'Infrastructure as Code concepts',
        ],
        'roadmap': [
            {'phase': 'Linux & Cloud', 'duration': '1–2 months',
             'tasks': ['Linux basics', 'Cloud fundamentals', 'AWS/Azure free tier projects']},
            {'phase': 'Containers & IaC', 'duration': '2–3 months',
             'tasks': ['Docker mastery', 'Kubernetes basics', 'Terraform projects']},
            {'phase': 'Job Ready', 'duration': '1–2 months',
             'tasks': ['Get AWS certified', 'CI/CD project', 'Apply to DevOps roles']},
        ],
        'learning_resources': [
            {'name': 'KodeKloud', 'type': 'Paid', 'url': 'https://kodekloud.com'},
            {'name': 'Linux Foundation', 'type': 'Free/Paid', 'url': 'https://training.linuxfoundation.org'},
            {'name': 'Play with Docker', 'type': 'Free', 'url': 'https://labs.play-with-docker.com'},
            {'name': 'AWS Free Tier', 'type': 'Free', 'url': 'https://aws.amazon.com/free'},
        ],
    },
}

# Default template for unknown roles
DEFAULT_CAREER_DATA = {
    'skills_to_learn': ['Problem Solving', 'Data Structures & Algorithms', 'System Design',
                        'Cloud Computing', 'Version Control (Git)', 'Communication Skills'],
    'certifications': ['Google IT Support', 'CompTIA A+', 'AWS Cloud Practitioner',
                       'IBM Professional Certificate'],
    'project_ideas': [
        'Build a portfolio project demonstrating your core skills',
        'Contribute to open-source projects on GitHub',
        'Create a tool that solves a real-world problem',
        'Build an API integration project',
        'Develop a web or mobile application end-to-end',
    ],
    'interview_topics': [
        'Core concepts of your target domain',
        'Problem-solving and algorithmic thinking',
        'Behavioral questions (STAR method)',
        'Industry-specific tools and technologies',
        'Your projects and the decisions you made',
        'Company research and fit assessment',
    ],
    'roadmap': [
        {'phase': 'Skill Building', 'duration': '1–2 months',
         'tasks': ['Identify skill gaps', 'Take relevant courses', 'Build practice projects']},
        {'phase': 'Portfolio', 'duration': '2–3 months',
         'tasks': ['Complete 2–3 portfolio projects', 'Get certifications', 'Update resume']},
        {'phase': 'Job Hunting', 'duration': '1–2 months',
         'tasks': ['Apply to 20+ jobs', 'Network on LinkedIn', 'Mock interviews']},
    ],
    'learning_resources': [
        {'name': 'Coursera', 'type': 'Free/Paid', 'url': 'https://coursera.org'},
        {'name': 'edX', 'type': 'Free/Paid', 'url': 'https://edx.org'},
        {'name': 'YouTube', 'type': 'Free', 'url': 'https://youtube.com'},
        {'name': 'GitHub', 'type': 'Free', 'url': 'https://github.com'},
    ],
}


def detect_target_domain(target_role: str) -> str:
    """Map target role string to a known domain key."""
    role_lower = target_role.lower()
    domain_map = {
        'software developer': ['software', 'developer', 'programmer', 'engineer', 'coding', 'backend', 'full stack'],
        'data scientist': ['data scientist', 'ml engineer', 'machine learning', 'ai engineer', 'deep learning', 'data science'],
        'web developer': ['web developer', 'frontend', 'front end', 'react', 'angular', 'vue', 'javascript developer'],
        'devops engineer': ['devops', 'sre', 'cloud engineer', 'infrastructure', 'platform engineer'],
    }
    for domain, keywords in domain_map.items():
        if any(kw in role_lower for kw in keywords):
            return domain
    return 'general'


def generate_career_suggestions(extracted: dict, target_role: str) -> dict:
    """
    Generate comprehensive career suggestions based on resume and target role.
    """
    domain = detect_target_domain(target_role)
    career_data = CAREER_DATA.get(domain, DEFAULT_CAREER_DATA)

    resume_skills_lower = {
        s.lower() for s in (
            extracted.get('skills', {}).get('technical', []) +
            extracted.get('skills', {}).get('soft', [])
        )
    }

    # Filter: suggest skills not already in resume
    skills_to_learn = [
        s for s in career_data['skills_to_learn']
        if s.lower() not in resume_skills_lower
    ][:6]

    # Current skill strengths
    current_strengths = extracted.get('skills', {}).get('technical', [])[:8]

    # Generate interview questions based on skills
    interview_questions = _generate_interview_questions(target_role, extracted)

    # Placement tips
    placement_tips = _get_placement_tips(extracted)

    return {
        'target_role': target_role,
        'domain': domain,
        'current_skills': current_strengths,
        'skills_to_learn': skills_to_learn,
        'certifications': career_data['certifications'],
        'project_ideas': career_data['project_ideas'],
        'interview_questions': interview_questions,
        'roadmap': career_data['roadmap'],
        'learning_resources': career_data['learning_resources'],
        'placement_tips': placement_tips,
        'skill_gap_count': len(skills_to_learn),
        'estimated_prep_time': _estimate_prep_time(extracted, target_role),
    }


def _generate_interview_questions(target_role: str, extracted: dict) -> list:
    """Generate relevant interview questions."""
    skills = extracted.get('skills', {}).get('technical', [])[:5]
    projects = extracted.get('projects', [])[:2]

    questions = [
        f'Tell me about yourself and why you are interested in this {target_role} role.',
        'What is your greatest technical achievement and what did you learn from it?',
        'Describe a challenging technical problem you solved and your approach.',
        'How do you stay updated with the latest industry trends and technologies?',
        'Describe a time you worked in a team — what was your contribution?',
    ]

    # Add skill-specific questions
    for skill in skills[:3]:
        questions.append(f'How have you used {skill} in your projects or work?')

    # Add project questions
    for proj in projects[:2]:
        questions.append(f'Walk me through the technical decisions you made for your "{proj[:40]}" project.')

    questions.extend([
        'What are your career goals for the next 2–3 years?',
        'Why do you want to work at this company?',
        'What makes you a good fit for this role?',
    ])

    return questions[:12]


def _get_placement_tips(extracted: dict) -> list:
    """Get placement preparation tips."""
    tips = [
        'Apply to 10–15 companies simultaneously — don\'t wait for one response before applying elsewhere.',
        'Customize your resume for each job application — add relevant keywords from the JD.',
        'Build a strong LinkedIn presence and connect with professionals in your target role.',
        'Practice DSA on LeetCode (Easy/Medium) — most tech companies test this.',
        'Prepare 3–5 STAR (Situation, Task, Action, Result) stories for behavioral questions.',
        'Research the company before every interview — understand their products and culture.',
        'Follow up after every interview with a thank-you email within 24 hours.',
    ]

    if not extracted.get('linkedin'):
        tips.insert(0, 'Set up a professional LinkedIn profile — 85% of recruiters use LinkedIn.')

    if not extracted.get('github') and extracted.get('skills', {}).get('technical'):
        tips.insert(1, 'Create a GitHub profile and push all your projects — it is your live portfolio.')

    if not extracted.get('certifications'):
        tips.append('Complete at least 1 recognized certification — it builds credibility.')

    return tips[:8]


def _estimate_prep_time(extracted: dict, target_role: str) -> str:
    """Estimate preparation time needed."""
    skills = extracted.get('skills', {}).get('technical', [])
    experience = extracted.get('experience', [])
    projects = extracted.get('projects', [])
    certs = extracted.get('certifications', [])

    readiness_score = 0
    if len(skills) >= 10:
        readiness_score += 30
    elif len(skills) >= 5:
        readiness_score += 15

    if experience:
        readiness_score += 25
    if projects:
        readiness_score += 20
    if certs:
        readiness_score += 15

    if readiness_score >= 70:
        return '1–2 months'
    elif readiness_score >= 40:
        return '2–4 months'
    else:
        return '4–6 months'
