"""
Verification test suite for AI Resume Screening Pro / ResumeAI Pro.
Covers route availability, auth, PDF extraction, ATS analysis, Job Match,
Rejection Analyzer, free-plan quotas, premium gating, Resume Editor CRUD
(autosave/duplicate/delete/preview/PDF export), resume deletion & quota release,
Contact page, FAQ section, report history, safe-redirect guard, and payment
signature verification primitives.

Run with:  python test_app.py
"""
import os
import hmac
import hashlib

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app import create_app
from extensions import db
from models import (
    User, Resume, JobMatch, UserSubscription,
    ResumeDoc, GeneratedReport, ContactMessage,
)
from services.payment_service import verify_payment_signature, verify_webhook_signature


def create_sample_pdf(filepath):
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 750, "John Doe")
    c.drawString(100, 735, "john.doe@example.com | +91 9876543210 | Mumbai, India")
    c.drawString(100, 720, "LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe")

    c.drawString(100, 690, "Professional Summary")
    c.drawString(100, 675, "Experienced Software Engineer with 3+ years of experience developing Python, Flask, and React web apps.")
    c.drawString(100, 660, "Spearheaded backend architecture and optimized SQL databases, achieving 40% performance gain.")

    c.drawString(100, 630, "Technical Skills")
    c.drawString(100, 615, "Python, Java, JavaScript, React, Flask, Django, SQL, PostgreSQL, Docker, Git, AWS, REST API, Agile")

    c.drawString(100, 585, "Work Experience")
    c.drawString(100, 570, "Software Developer - Tech Corp (2021 - Present)")
    c.drawString(100, 555, "- Built microservices using Python and Flask, handling 100k daily active requests.")
    c.drawString(100, 540, "- Automated CI/CD pipelines reducing deployment time by 50%.")

    c.drawString(100, 510, "Education")
    c.drawString(100, 495, "B.Tech in Computer Science - ABC University (2017 - 2021), CGPA 8.5/10")

    c.drawString(100, 465, "Projects")
    c.drawString(100, 450, "AI Resume Screener - Built with Python, Flask, and React to analyze resume ATS scores.")

    c.drawString(100, 420, "Certifications")
    c.drawString(100, 405, "AWS Certified Solutions Architect, Coursera Deep Learning Specialization")

    c.save()


def run_tests():
    app = create_app('testing')
    client = app.test_client()

    print("--- 1. Testing Unauthenticated Route Availability ---")
    routes_to_test = [
        ('/', 200),
        ('/login', 200),
        ('/register', 200),
        ('/pricing', 200),
        ('/forgot-password', 200),
        ('/contact', 200),          # NEW public contact page
    ]
    for route, expected_status in routes_to_test:
        res = client.get(route)
        assert res.status_code == expected_status, f"Route {route} failed with {res.status_code}"
        print(f"[OK] Route {route} -> {res.status_code}")

    # Landing page must contain How It Works anchor target, testimonials, FAQ
    index_res = client.get('/')
    assert b'id="how-it-works"' in index_res.data, "Landing page missing #how-it-works section"
    assert b'id="testimonials"' in index_res.data, "Landing page missing testimonials section"
    assert b'id="faq"' in index_res.data, "Landing page missing FAQ section"
    assert b'Sample testimonials shown for illustration' in index_res.data, "Testimonials not labelled as SAMPLE"
    print("[OK] Landing page sections verified (How It Works / Testimonials / FAQ)")

    print("\n--- 2. Testing User Registration & Login ---")
    reg_res = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert reg_res.status_code == 200, "Registration failed"
    print("[OK] User registered and logged in successfully!")

    print("\n--- 3. Testing Open-Redirect Guard on Login ---")
    # A malicious absolute next URL must NOT be followed after login
    evil_login = client.post('/login?next=https://evil.example.com/steal', data={
        'email': 'test@example.com',
        'password': 'Password123'
    })
    assert evil_login.status_code == 302, "Expected redirect after login"
    location = evil_login.headers.get('Location', '')
    assert 'evil.example.com' not in location, f"Open redirect still possible! Location={location}"
    print(f"[OK] Malicious next URL ignored -> redirected to: {location}")

    print("\n--- 4. Testing Authenticated Pages (Free User) ---")
    auth_routes = ['/dashboard', '/scanner', '/history', '/profile', '/settings', '/reports', '/editor']
    for route in auth_routes:
        res = client.get(route)
        assert res.status_code == 200, f"Authenticated route {route} failed with {res.status_code}"
        print(f"[OK] Authenticated Route {route} -> {res.status_code}")

    print("\n--- 5. Testing PDF Resume Upload & Free Quota Enforcement ---")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    sample_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sample_test_resume.pdf')
    create_sample_pdf(sample_pdf_path)

    for i in range(1, 4):
        with open(sample_pdf_path, 'rb') as pdf_file:
            upload_res = client.post('/scanner', data={
                'resume': (pdf_file, f'test_resume_{i}.pdf')
            }, follow_redirects=True)
            assert upload_res.status_code == 200, f"Resume upload {i} failed"
            print(f"[OK] Resume Upload {i} successful!")

    with open(sample_pdf_path, 'rb') as pdf_file:
        quota_res = client.post('/scanner', data={
            'resume': (pdf_file, 'test_resume_4.pdf')
        }, follow_redirects=True)
        assert quota_res.status_code == 200
        assert b"Free plan is limited to 3 resume analyses" in quota_res.data
        print("[OK] Free Plan 3-Resume Upload Quota Enforcement verified!")

    with app.app_context():
        resume = Resume.query.first()
        assert resume is not None, "Resume not saved in DB"
        print(f"[OK] Saved Resume ID: {resume.id}, ATS Score: {resume.ats_score}")

        analysis_res = client.get(f'/analysis/{resume.id}')
        assert analysis_res.status_code == 200
        print("[OK] Resume Analysis route verified!")

    print("\n--- 6. Testing Job Description Match & Free Quota Enforcement ---")
    with app.app_context():
        resume = Resume.query.first()
        jd_text = """
        We are looking for a Senior Data Scientist / ML Engineer with 5+ years of experience.
        Required Skills: Python, TensorFlow, PyTorch, Kubernetes, MLOps, C++, Scala, Kafka.
        Education: Master's degree in Machine Learning or Data Science.
        """

        for j in range(1, 3):
            match_res = client.post('/job-match', data={
                'resume_id': str(resume.id),
                'job_title': f'Job Role {j}',
                'company': 'Tech Corp',
                'job_description': jd_text
            }, follow_redirects=True)
            assert match_res.status_code == 200, f"Job Match {j} failed"
            print(f"[OK] Job Match {j} successful!")

        match_quota_res = client.post('/job-match', data={
            'resume_id': str(resume.id),
            'job_title': 'Job Role 3',
            'company': 'Tech Corp',
            'job_description': jd_text
        }, follow_redirects=True)
        assert match_quota_res.status_code == 200
        assert b"Free plan is limited to 2 job description matches" in match_quota_res.data
        print("[OK] Free Plan 2-Job Match Quota Enforcement verified!")

    print("\n--- 7. Testing Premium Route Gating (Free User Restricted) ---")
    with app.app_context():
        resume = Resume.query.first()
        job_match = JobMatch.query.first()

        pro_routes = [
            f'/rejection-analysis/{job_match.id}',
            f'/linkedin/{resume.id}',
            f'/naukri/{resume.id}',
            f'/career/{resume.id}',
            f'/reports/{resume.id}/download',
            '/resume-builder'
        ]
        for route in pro_routes:
            res = client.get(route)
            assert res.status_code == 200
            assert b"Premium Feature" in res.data or b"PRO" in res.data
            print(f"[OK] Route Gating Verified for Free User -> {route}")

    print("\n--- 8. Testing Upgrade to PRO & Premium Access ---")
    with app.app_context():
        user = User.query.first()
        sub = UserSubscription.query.filter_by(user_id=user.id).first()
        sub.plan = 'pro'
        sub.status = 'active'
        db.session.commit()
        print("[OK] Account upgraded to PRO Plan in DB!")

    with app.app_context():
        resume = Resume.query.first()
        job_match = JobMatch.query.first()

        rejection_res = client.get(f'/rejection-analysis/{job_match.id}')
        assert rejection_res.status_code == 200
        assert b"AI Screening-Based Rejection Reasons" in rejection_res.data
        # Exact product-required disclaimer wording must be present
        # (whitespace-normalized: HTML source may wrap the sentence across lines)
        normalized = b' '.join(rejection_res.data.split())
        required_disclaimer = ("This analysis is AI-generated guidance and does not represent "
                               "an actual employer hiring decision.").encode()
        assert required_disclaimer in normalized, "Exact disclaimer sentence missing!"
        print("[OK] PRO Access to Rejection Analyzer + exact disclaimer verified!")

        linkedin_res = client.get(f'/linkedin/{resume.id}')
        assert linkedin_res.status_code == 200
        print("[OK] PRO Access to LinkedIn Optimizer verified!")

        naukri_res = client.get(f'/naukri/{resume.id}')
        assert naukri_res.status_code == 200
        print("[OK] PRO Access to Naukri Optimizer verified!")

        career_res = client.get(f'/career/{resume.id}')
        assert career_res.status_code == 200
        print("[OK] PRO Access to Career Assistant verified!")

        report_res = client.get(f'/reports/{resume.id}/download')
        assert report_res.status_code == 200
        assert report_res.content_type.startswith('application/pdf'), \
            f"Expected PDF, got {report_res.content_type}"
        print("[OK] PRO Access to PDF Report Download verified!")

        rej_pdf = client.get(f'/rejection-analysis/{job_match.id}/download')
        assert rej_pdf.status_code == 200
        assert rej_pdf.content_type.startswith('application/pdf')
        print("[OK] Dedicated Rejection Analysis PDF download verified!")

    print("\n--- 9. Testing Report History Persistence ---")
    with app.app_context():
        user = User.query.first()
        reports = GeneratedReport.query.filter_by(user_id=user.id).all()
        kinds = {r.kind for r in reports}
        assert 'analysis' in kinds, "Analysis report not registered in history"
        assert 'rejection' in kinds, "Rejection report not registered in history"

        first_report = GeneratedReport.query.filter_by(user_id=user.id).first()
        file_res = client.get(f'/reports/{first_report.id}/file')
        assert file_res.status_code == 200
        print(f"[OK] GeneratedReport history persisted ({len(reports)} rows) and re-download works!")

    print("\n--- 10. Testing Resume Editor CRUD / Autosave / Preview / Export ---")
    with app.app_context():
        user = User.query.first()

        # Create
        create_res = client.post('/editor/create', data={'title': 'SDE Resume 2026'},
                                 follow_redirects=True)
        assert create_res.status_code == 200
        doc = ResumeDoc.query.filter_by(user_id=user.id, title='SDE Resume 2026').first()
        assert doc is not None, "Resume doc was not created"
        print(f"[OK] Resume doc created (ID {doc.id})")

        doc_id = doc.id

        # Edit page renders
        edit_res = client.get(f'/editor/{doc_id}/edit')
        assert edit_res.status_code == 200
        assert b'docTitle' in edit_res.data
        print("[OK] Editor form page renders!")

        # Manual save (JSON payload)
        payload = {
            'title': 'SDE Resume 2026',
            'data': {
                'full_name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '+91 9876543210',
                'location': 'Mumbai',
                'linkedin': 'https://linkedin.com/in/johndoe',
                'github': 'https://github.com/johndoe',
                'website': '',
                'summary': 'Software engineer with 3 years of experience building scalable web apps.',
                'skills': ['Python', 'Flask', 'React', 'SQL', 'Docker'],
                'education': [{'degree': 'B.Tech CSE', 'institution': 'ABC University',
                               'start_year': '2017', 'end_year': '2021', 'grade': '8.5 CGPA'}],
                'experience': [{'title': 'Software Developer', 'company': 'Tech Corp',
                                'location': 'Mumbai', 'start': '2021', 'end': 'Present',
                                'bullets': ['Built microservices handling 100k daily requests.']}],
                'internships': [],
                'projects': [{'name': 'Resume Screener', 'tech': 'Python, Flask',
                              'description': 'ATS analyzer.', 'link': ''}],
                'certifications': [{'name': 'AWS SAA', 'issuer': 'Amazon', 'year': '2024'}],
                'achievements': ['Hackathon winner'],
                'languages': ['English', 'Hindi'],
                'template': 'modern',
            }
        }
        save_res = client.post(f'/editor/{doc_id}/save', json=payload)
        assert save_res.status_code == 200
        assert save_res.get_json()['success'] is True
        print("[OK] Manual JSON save verified!")

        # Autosave endpoint
        autosave_res = client.post(f'/editor/{doc_id}/autosave', json=payload)
        assert autosave_res.status_code == 200
        assert autosave_res.get_json()['success'] is True
        print("[OK] Autosave endpoint verified!")

        # Data actually persisted & normalized
        with app.app_context():
            fresh = db.session.get(ResumeDoc, doc_id)
            stored = fresh.get_data()
            assert stored['full_name'] == 'John Doe'
            assert len(stored['experience']) == 1
            assert stored['experience'][0]['bullets'] == ['Built microservices handling 100k daily requests.']
            assert len(stored['education']) == 1
        print("[OK] Document data persisted correctly!")

        # Preview page shows real content (no fake placeholders)
        preview_res = client.get(f'/editor/{doc_id}/preview')
        assert preview_res.status_code == 200
        assert b'John Doe' in preview_res.data
        assert b'Built microservices handling 100k daily requests.' in preview_res.data
        assert b'Software Engineer / Technical Specialist' not in preview_res.data  # old fake content gone
        print("[OK] Preview renders real document content (no fake data)!")

        # PDF export
        export_res = client.get(f'/editor/{doc_id}/export-pdf')
        assert export_res.status_code == 200
        assert export_res.content_type.startswith('application/pdf')
        print("[OK] Resume PDF export verified!")

        # Duplicate
        dup_res = client.post(f'/editor/{doc_id}/duplicate', follow_redirects=True)
        assert dup_res.status_code == 200
        with app.app_context():
            copies = ResumeDoc.query.filter(
                ResumeDoc.title.like('%(Copy)%')).count()
            assert copies >= 1, "Duplicate not created"
        print("[OK] Duplicate verified!")

        # Ownership enforcement: second user cannot touch this doc
        client.get('/logout')
        client.post('/register', data={
            'name': 'Other User', 'email': 'other@example.com',
            'password': 'Password123', 'confirm_password': 'Password123'
        }, follow_redirects=True)
        forbidden_save = client.post(f'/editor/{doc_id}/save', json=payload)
        assert forbidden_save.status_code == 403, "Cross-user editor access not blocked!"
        forbidden_edit = client.get(f'/editor/{doc_id}/edit')
        assert forbidden_edit.status_code == 403
        print("[OK] Editor ownership enforcement verified!")
        client.get('/logout')

        # Log back in as primary user and delete the copy
        client.post('/login', data={'email': 'test@example.com', 'password': 'Password123'},
                    follow_redirects=True)
        with app.app_context():
            copy_doc = ResumeDoc.query.filter(ResumeDoc.title.like('%(Copy)%')).first()
            copy_id = copy_doc.id
        del_res = client.post(f'/editor/{copy_id}/delete', follow_redirects=True)
        assert del_res.status_code == 200
        with app.app_context():
            assert db.session.get(ResumeDoc, copy_id) is None, "Delete did not remove the doc"
        print("[OK] Delete verified!")

    print("\n--- 11. Testing Resume Deletion Frees Free-Plan Quota ---")
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        active_resumes = Resume.query.filter_by(user_id=user.id, is_active=True).all()
        assert len(active_resumes) >= 3
        victim = active_resumes[0]
        victim_id = victim.id

    del_resume = client.post(f'/resume/{victim_id}/delete', follow_redirects=True)
    assert del_resume.status_code == 200

    with open(sample_pdf_path, 'rb') as pdf_file:
        freed_upload = client.post('/scanner', data={
            'resume': (pdf_file, 'test_resume_after_delete.pdf')
        }, follow_redirects=True)
        assert freed_upload.status_code == 200
        assert b"Free plan is limited to 3 resume analyses" not in freed_upload.data, \
            "Quota should have been freed after deletion!"
    print("[OK] Deleting a resume frees a free-plan upload slot!")

    print("\n--- 12. Testing Contact Page Submission ---")
    contact_post = client.post('/contact', data={
        'name': 'Interested Candidate',
        'email': 'candidate@example.com',
        'subject': 'Plan question',
        'message': 'Do you offer team discounts for the Business plan?'
    }, follow_redirects=True)
    assert contact_post.status_code == 200
    with app.app_context():
        msg = ContactMessage.query.filter_by(email='candidate@example.com').first()
        assert msg is not None, "Contact message not stored"
    print("[OK] Contact form stores messages in database!")

    print("\n--- 13. Testing Payment Signature Primitives ---")
    secret = 'unit_test_secret_key'
    order_id, payment_id = 'order_test123', 'pay_test456'
    msg = f"{order_id}|{payment_id}".encode()
    good_sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    bad_sig = '0' * 64

    assert verify_payment_signature(secret, order_id, payment_id, good_sig) is True
    assert verify_payment_signature(secret, order_id, payment_id, bad_sig) is False
    assert verify_payment_signature('', order_id, payment_id, good_sig) is False
    print("[OK] Order-payment HMAC signature verification (accept/reject/no-secret) verified!")

    body = b'{"event":"payment.captured"}'
    wh_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(secret, body, wh_sig) is True
    assert verify_webhook_signature(secret, body, bad_sig) is False
    assert verify_webhook_signature('', body, wh_sig) is False
    print("[OK] Webhook HMAC signature verification (accept/reject/no-secret) verified!")

    # Webhook endpoint must be reachable without CSRF token (server-to-server)
    webhook_no_sig = client.post('/payment/webhook', data=body,
                                 content_type='application/json')
    assert webhook_no_sig.status_code == 400, \
        "Webhook should reject missing signature with 400 (not CSRF-blocked!)"
    print("[OK] Webhook endpoint accepts server-to-server POSTs (CSRF-exempt, signature-gated)!")

    print("\n==================================================")
    print("ALL TEST SUITE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == '__main__':
    run_tests()