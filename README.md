# AI Resume Screening Pro

A production-style Flask SaaS platform that analyzes resumes against real ATS (Applicant Tracking System) criteria, matches them to job descriptions, explains likely screening rejections with AI-generated guidance, and helps candidates optimize their LinkedIn/Naukri profiles — all backed by a real NLP parsing pipeline (no fake scores, ever).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Folder Structure](#folder-structure)
4. [Architecture](#architecture)
5. [Installation](#installation)
6. [Requirements](#requirements)
7. [Environment Variables](#environment-variables)
8. [Database Setup](#database-setup)
9. [Running the Project](#running-the-project)
10. [Screenshots](#screenshots-placeholder)
11. [API Overview](#api-overview)
12. [Resume Upload Flow](#resume-upload-flow)
13. [ATS Flow](#ats-flow)
14. [AI Rejection Analyzer](#ai-rejection-analyzer)
15. [Resume Builder](#resume-builder)
16. [Resume Editor](#resume-editor)
17. [Reports](#reports)
18. [Pricing & Subscriptions](#pricing--subscriptions)
19. [Razorpay Payments](#razorpay-payments)
20. [Deployment Guide](#deployment-guide)
21. [Testing](#testing)
22. [Troubleshooting](#troubleshooting)
23. [Contributing](#contributing)
24. [License](#license)
25. [Future Roadmap](#future-roadmap)

---

## Project Overview

**AI Resume Screening Pro** is a full-stack Flask application for job seekers:

- Upload a text-based PDF resume → it is parsed with pdfplumber/PyPDF2 (+ optional spaCy NER).
- A weighted **ATS score** is computed from what was *actually detected* in your document.
- Compare your resume against any job description using **TF-IDF cosine similarity** plus skill-gap analysis.
- The **AI Rejection Analyzer** explains, in plain language, why a resume might be filtered for a specific job — clearly labelled as AI screening guidance, never as an actual employer decision.
- Build new resumes in the multi-section **Resume Editor** (autosave, duplicate, preview, PDF export).
- Optimize your **LinkedIn** and **Naukri.com** presence from parsed resume data.
- Get a personalized **Career Roadmap** with skills, certifications, projects, interview questions, and prep timelines.
- Download professional **PDF reports**; every generated report is stored in your history.
- Monetized via **Free / PRO / Business** plans with Razorpay checkout.

---

## Features

| Area | What you get |
|---|---|
| Authentication | Register, login/logout, remember-me, password reset (email when SMTP configured, dev link otherwise), change password |
| Resume Upload | Drag-&-drop PDF upload, 10 MB limit, PDF-only validation, UUID filenames, free-plan quota (3 active scans) |
| Resume Parsing | Skills (tech + soft), education, experience, internships, projects, certifications, achievements, languages, contact info, action verbs, measurable achievements |
| ATS Analyzer | Weighted component scores (skills/keywords/formatting/education/experience/projects/summary/measurable), strengths, gaps, suggestions, legacy-record enrichment |
| Job Matching | TF-IDF cosine similarity, JD keyword extraction, matching/missing skills, role-domain detection, education/experience fit, 3-tier decision |
| AI Rejection Analyzer | Critical/major/minor reasons, primary reason, improvement plan with priorities, current → potential match score, exact disclaimer wording, dedicated PDF report |
| Resume Builder | Quick form-based builder with live preview (PRO) |
| Resume Editor | Multi-section documents (personal, summary, skills, education, experience, internships, projects, certifications, achievements, languages, social links), autosave every 25 s, manual save, duplicate, delete, preview, ReportLab PDF export |
| Dashboard | Stats cards, latest ATS circle + Chart.js breakdown, quick actions, latest AI screening result banner, recent matches table |
| Reports Hub | Per-resume download cards + full report generation history with re-download |
| History | All scanned resumes and job-match evaluations with delete support |
| Career Assistant | Role playbooks (software/data/web/devops + generic), skill gaps, certifications, project ideas, interview questions, roadmap timeline, placement tips |
| LinkedIn Optimizer | Profile score + breakdown, headline ideas, About template, visibility/networking tips, safe copy-to-clipboard |
| Naukri Optimizer | Naukri score, search visibility, keyword density, popular-keyword gaps, ranking + recruiter playbooks |
| Pricing | Free / PRO ₹59 / Business ₹99 with server-enforced feature gating (`require_plan` decorator) |
| Razorpay | Order creation → Checkout.js → HMAC-SHA256 verify → 30-day subscription activation; signature-gated webhook that also fulfils purchases and handles failures |
| Landing Page | Hero, features, How It Works, sample testimonials ("Loved by Professionals"), FAQ accordion, CTA, footer |
| Contact | Public contact form persisting messages to the database |
| Security | CSRF on all internal forms/AJAX, open-redirect guard, rate limiting on auth endpoints, security headers, ownership checks on every ID-scoped route |

---

## Folder Structure

```
AI_Resume_Screening_Pro/
├── app.py                  # Application factory, error handlers, security headers, index bootstrap
├── config.py               # Dev / Prod / Test configs, pricing table
├── extensions.py           # db, login_manager, csrf, mail singletons
├── models.py               # SQLAlchemy models (User, Resume, JobMatch, reports, docs, payments…)
├── forms.py                # WTForms definitions
├── utils.py                # Plan gating decorator, quotas, rate limiter, safe-redirect helper
├── wsgi.py                 # Gunicorn entry point
├── test_app.py             # End-to-end smoke/regression suite (python test_app.py)
├── requirements.txt
├── .env.example            # Copy to .env and fill in
│
├── routes/
│   ├── auth.py             # register / login / logout / forgot / reset
│   ├── main.py             # landing, dashboard, history, pricing, profile, settings, contact
│   ├── scanner.py          # upload, analysis, job-match, rejection, linkedin, naukri,
│   │                       # career, resume-builder, extracted-field editor, reports hub,
│   │                       # report downloads, resume delete
│   ├── payment.py          # create-order, verify, success/failed pages, webhook (CSRF-exempt)
│   ├── editor.py           # NEW: Resume Editor CRUD / autosave / preview / export-pdf
│   └── api.py              # JSON API (/api/resume/<id>/ats-score)
│
├── services/
│   ├── resume_parser.py    # PDF text extraction + structured field extraction
│   ├── ats_analyzer.py     # Weighted ATS scoring engine
│   ├── job_matcher.py      # TF-IDF matcher + skill-gap analysis
│   ├── rejection_analyzer.py   # Screening-reason engine (two scopes)
│   ├── career_service.py   # Roadmaps / interview prep / placement tips
│   ├── linkedin_service.py # LinkedIn profile optimization reports
│   ├── naukri_service.py   # Naukri ranking optimization reports
│   ├── payment_service.py  # Razorpay client, order creation, HMAC verifications
│   ├── report_service.py   # ReportLab: analysis PDF, rejection PDF, resume export PDF
│   └── email_service.py    # Flask-Mail transactional email (graceful dev fallback)
│
├── templates/
│   ├── base.html           # Sidebar layout (authed) + marketing navbar (anon)
│   ├── auth/               # login, register, forgot_password, reset_password
│   ├── pages/              # index, dashboard, history, pricing, profile, settings,
│   │                       # premium_lock, payment_success, payment_failed, reports, contact
│   ├── scanner/            # upload, analysis, job_match_form/result, rejection_analysis,
│   │                       # linkedin, naukri, career, resume_builder(+preview),
│   │                       # resume_editor (extracted-fields), editor_list/form/preview,
│   │                       # _editor_entry_* partials
│   ├── emails/             # reset_password.html (HTML email)
│   └── errors/             # 403, 404, 500
│
└── static/
    ├── css/style.css       # Dark glassmorphism theme + print styles
    ├── js/main.js          # Upload drag-drop, copy buttons, Razorpay helper
    └── images/             # (reserved for logos/screenshots)
```

Runtime-created directories (gitignored): `uploads/`, `reports/`, `instance/`, `resume_screening.db`.

---

## Architecture

```
Browser ──► Flask Blueprints (routes/)
              │            │
              │            └── Jinja2 templates (Bootstrap 5 + custom dark glass theme)
              ▼
        Services layer (services/)         ← all business logic lives here
              │
              ▼
        SQLAlchemy models (models.py) ──► SQLite (dev) / Postgres-ready (prod URI swap)

Payments:  Browser ⇄ Razorpay Checkout.js ⇄ /payment/create-order + /payment/verify
           Razorpay servers ──► /payment/webhook (HMAC-SHA256 verified, CSRF-exempt)
```

Key design decisions:

- **Application factory** pattern (`create_app`) so tests can spin up isolated apps.
- **Services own the logic** — routes stay thin; analyzers are pure functions over dicts.
- **No fabricated data**: if the parser cannot detect something, the UI says "Not detected" instead of inventing values.
- **Idempotent payments**: replaying `/payment/verify` or receiving duplicate webhooks never double-extends a subscription.
- **Backward compatibility**: `enrich_ats_display()` upgrades older stored analysis JSON at read time.

---

## Installation

```bash
# 1. Clone
git clone <your-repo-url> AI_Resume_Screening_Pro
cd AI_Resume_Screening_Pro

# 2. Create a virtual environment (Python 3.10+ recommended)
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional but recommended) spaCy English model for better name detection
python -m spacy download en_core_web_sm

# 5. Configure environment
copy .env.example .env         # Windows
cp .env.example .env           # macOS/Linux
#   then edit .env with your keys

# 6. Run
python app.py                  # http://127.0.0.1:5000
```

---

## Requirements

See [`requirements.txt`](requirements.txt). Core stack:

- Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Mail
- SQLAlchemy 2.x, WTForms, email-validator
- pdfplumber, PyPDF2 (PDF text extraction)
- spaCy *(optional model)*, NLTK, scikit-learn (NLP / TF-IDF)
- ReportLab (PDF generation), Razorpay SDK, python-dotenv, Gunicorn

No additional packages are required by this project beyond `requirements.txt`.

---

## Environment Variables

Copy `.env.example` → `.env`:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Long random string; sessions/CSRF signing. **Must change in production.** |
| `DATABASE_URL` | – | Defaults to `sqlite:///resume_screening.db`. Use `postgresql://…` in production. |
| `FLASK_ENV` | – | `development` (default) or `production`. |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | For payments | Test-mode keys from the Razorpay dashboard. Empty ⇒ checkout returns a friendly "not configured" message. |
| `RAZORPAY_WEBHOOK_SECRET` | For webhooks | Webhook secret from the Razorpay dashboard. |
| `MAIL_SERVER` / `MAIL_PORT` / `MAIL_USE_TLS` | – | SMTP settings (defaults: Gmail :587 TLS). |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | For email | When set, password-reset emails are actually sent; otherwise the dev fallback flashes the reset link. |
| `MAIL_DEFAULT_SENDER` | – | From-address for outgoing mail. |

---

## Database Setup

- **Dev:** SQLite is created automatically at first start (`db.create_all()` + idempotent performance indexes). Delete `resume_screening.db` to reset.
- **Schema changes:** this project currently uses `create_all()` (creates missing tables). For destructive changes on an existing database, migrate manually or adopt Flask-Migrate (see Roadmap).
- **Production:** point `DATABASE_URL` at PostgreSQL; the app normalizes legacy `postgres://` URIs automatically.

---

## Running the Project

```bash
python app.py          # Development server on http://127.0.0.1:5000
```

Production:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

Run the regression suite:

```bash
python test_app.py
```

---

## Screenshots Placeholder

> _Add screenshots here:_
> - Landing page hero
> - Dashboard with ATS chart
> - Analysis page with rejection banner
> - Resume Editor with autosave toolbar
> - Reports hub with history table
> - Pricing page

---

## API Overview

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/resume/<id>/ats-score` | owner | JSON: all ATS component scores + analysis blob |
| POST | `/editor/<id>/save` | owner | Persist an editor document (JSON) |
| POST | `/editor/<id>/autosave` | owner | Same as save, flagged as autosave |
| POST | `/payment/create-order` | user | Create a Razorpay order for a plan |
| POST | `/payment/verify` | user | Verify checkout signature, activate subscription (idempotent) |
| POST | `/payment/webhook` | signature | Razorpay webhook: captured/authorized fulfilment, failed handling |

---

## Resume Upload Flow

```
/scanner (POST multipart)
  ├─ quota check (free = 3 active resumes)      → premium_lock page if exceeded
  ├─ extension + size validation (PDF ≤ 10 MB)  → 413 handler / flash errors
  ├─ save to uploads/<uuid>_<name>.pdf
  ├─ parse_resume()                             → structured dict + raw_text
  ├─ empty-text guard                           → clear error for scanned/image PDFs
  ├─ calculate_ats_score()
  ├─ persist Resume row (extracted JSON + analysis JSON + column scores)
  └─ redirect → /analysis/<id>
```

---

## ATS Flow

1. Eight component scorers run over the parsed data (skills 30 %, keywords 20 %, formatting 15 %, education 10 %, experience 10 %, projects 8 %, summary 4 %, measurable achievements 3 %).
2. Results aggregate into an overall score with a label/color band (Poor → Excellent).
3. `detect_factual_strengths()` lists only evidence actually found; `collect_ats_gaps()` lists missing keywords/sections/skills.
4. Older records are upgraded on read via `enrich_ats_display()`.

---

## AI Rejection Analyzer

Two complementary views:

- **Resume-scoped** (`build_resume_rejection_view`) — embedded on the analysis page; risk level, why-explanation, formatting/section issues, prioritized improvement plan.
- **Job-scoped** (`analyze_rejection`) — full page + PDF for a specific JobMatch; critical/major/minor reasons, primary reason, missing skills/keywords, estimated improved match.

Every surface carries the required disclaimer:

> **This analysis is AI-generated guidance and does not represent an actual employer hiring decision.**

---

## Resume Builder

Quick PRO-gated form (contact + summary + skills + template choice) rendering a live preview with four visual styles. For fully-fledged resumes use the **Resume Editor** below.

---

## Resume Editor

Documents are stored per-user in the `resume_docs` table as validated JSON.

- Sections: personal info, social links, summary, skills, education, experience, internships, projects, certifications, achievements, languages.
- Multiple entries per section with add/remove controls.
- **Autosave** every 25 s while dirty + beforeunload guard; manual **Save** button with status indicator.
- **Preview** renders the real content in a print-friendly white paper layout (4 template styles).
- **Export PDF** generates a clean ReportLab resume and registers it in report history.
- Duplicate / delete supported; every endpoint enforces ownership (403 otherwise).

---

## Reports

- `/reports/<resume_id>/download` — comprehensive analysis PDF (candidate info, ATS tables, strengths/weaknesses, job match, rejection section).
- `/rejection-analysis/<job_match_id>/download` — dedicated rejection PDF with the mandatory disclaimer.
- `/editor/<doc_id>/export-pdf` — resume export.
- Every generation inserts a `GeneratedReport` row; the Reports Hub lists the last 20 with one-click re-download from disk.

---

## Pricing & Subscriptions

| Plan | Price | Includes |
|---|---|---|
| Free | ₹0 | 3 active resume scans, 2 job matches, basic ATS |
| PRO | ₹59/mo | Unlimited scans/matches, Rejection Analyzer, LinkedIn/Naukri optimizers, Career Assistant, Builder/Editor, PDF reports |
| Business | ₹99/mo | Everything in PRO + priority support (bulk-screening suite marked *Coming Soon*) |

Enforcement is server-side via the `@require_plan('pro')` decorator (JSON-aware for AJAX) plus explicit quota checks for uploads/job-matches. Deleting a resume frees its free-plan slot.

---

## Razorpay Payments

Happy path:

```
Pricing page ──POST /payment/create-order──► Razorpay Order created + pending Payment row
            ◄──order_id/amount/key──────────┘
Checkout.js opens ──user pays──► handler(response)
            ──POST /payment/verify──► HMAC-SHA256(order_id|payment_id, secret) verified
                                      ► Payment.status=success, subscription activated (30 days)
Webhook (independent safety net):
  payment.captured / authorized → fulfil + activate (idempotent)
  payment.failed                → mark failed
```

Security properties: constant-time signature comparison, plan/amount always sourced from our DB row, replay-safe verify, webhook gated purely by HMAC (CSRF-exempt by design).

---

## Deployment Guide

1. Provision a host (Render/Railway/EC2…) with Python 3.10+.
2. Set env vars from the table above (**production `SECRET_KEY`**, `FLASK_ENV=production`, Postgres `DATABASE_URL`, Razorpay live keys, SMTP creds).
3. `pip install -r requirements.txt && python -m spacy download en_core_web_sm`.
4. Start with Gunicorn: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2`.
5. Put HTTPS in front (session cookies become Secure automatically in production config).
6. In the Razorpay dashboard, add a webhook pointing to `https://<your-domain>/payment/webhook` subscribed to `payment.captured`, `payment.authorized`, `payment.failed`; copy the webhook secret into `RAZORPAY_WEBHOOK_SECRET`.
7. Optional: serve `static/` via CDN/nginx; mount `uploads/` and `reports/` on persistent storage.

---

## Testing

```bash
python test_app.py
```

The suite boots an isolated in-memory app and verifies: public/authenticated route availability, registration/login, the open-redirect guard, upload + parsing + real ATS scoring, both free-plan quotas, premium gating, PRO access after upgrade, the exact rejection disclaimer, analysis + rejection PDF downloads, report-history persistence and re-download, the complete editor lifecycle (create → edit → save → autosave → preview → export → duplicate → cross-user 403 → delete), resume deletion freeing quota, contact-form persistence, HMAC signature primitives, and webhook reachability without CSRF tokens.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Could not extract any text from this PDF" | The PDF is image-based/scanned. Export a text-based PDF. |
| Name not detected | Install the spaCy model: `python -m spacy download en_core_web_sm`. |
| Checkout says gateway not configured | Fill `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` in `.env`. |
| Reset link shown on screen instead of emailed | SMTP creds missing — set `MAIL_USERNAME`/`MAIL_PASSWORD`. |
| NLTK lookup errors on first run | They self-heal (punkt/stopwords auto-download); ensure internet access once. |
| Port already in use | Set `PORT=5001` (or another port) before `python app.py`. |

---

## Contributing

1. Fork & branch (`feature/my-change`).
2. Keep business logic in `services/`; keep routes thin.
3. Preserve the no-fake-data principle — never hardcode scores or reasons.
4. Add/extend coverage in `test_app.py` and run it before opening a PR.
5. Follow the existing style (type hints on services, docstrings on modules).

---

## License

© 2026 AI Resume Screening Pro. All rights reserved. (Add your chosen license here — MIT/Apache-2.0/etc.)

---

## Future Roadmap

- Flask-Migrate (Alembic) migrations for zero-downtime schema changes
- OCR pipeline (Tesseract) for scanned/image PDFs
- DOCX/TXT resume ingestion
- Semantic (embedding-based) job matching alongside TF-IDF
- Admin panel: users, subscriptions, contact messages, analytics
- Business-tier bulk screening & candidate comparison dashboards
- Redis-backed rate limiting + background task queue for large files
- Email verification flow & subscription renewal reminders