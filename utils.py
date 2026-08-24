"""
Utility decorators and helpers for subscription gating and feature access control,
lightweight rate limiting, and safe redirect validation.
"""
import time
import threading
from functools import wraps
from urllib.parse import urlparse

from flask import flash, redirect, url_for, request, render_template
from flask_login import current_user

PLAN_LEVELS = {
    'free': 0,
    'pro': 1,
    'business': 2,
}

FREE_LIMITS = {
    'resume_scans': 3,
    'job_matches': 2,
}


def require_plan(min_plan='pro'):
    """
    Decorator to gate routes based on minimum required user plan.
    If user is on Free plan and accesses Pro/Business feature,
    it shows upgrade notification or renders lock card.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            user_plan = current_user.get_plan()
            user_level = PLAN_LEVELS.get(user_plan, 0)
            required_level = PLAN_LEVELS.get(min_plan, 1)

            if user_level < required_level:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {
                        'error': 'premium_required',
                        'message': f'This feature requires a {min_plan.upper()} plan.',
                        'required_plan': min_plan
                    }, 403
                
                flash(f'🔒 This feature requires a {min_plan.upper()} subscription. Upgrade to unlock access!', 'warning')
                return render_template('pages/premium_lock.html', required_plan=min_plan)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def can_upload_resume(user):
    """Check if user has remaining resume upload quota."""
    if user.get_plan() in ('pro', 'business'):
        return True, None
    from models import Resume
    count = Resume.query.filter_by(user_id=user.id, is_active=True).count()
    if count >= FREE_LIMITS['resume_scans']:
        return False, f"Free plan is limited to {FREE_LIMITS['resume_scans']} resume analyses. Upgrade to PRO for unlimited scans!"
    return True, None


def can_run_job_match(user):
    """Check if user has remaining job match quota."""
    if user.get_plan() in ('pro', 'business'):
        return True, None
    from models import JobMatch
    count = JobMatch.query.filter_by(user_id=user.id).count()
    if count >= FREE_LIMITS['job_matches']:
        return False, f"Free plan is limited to {FREE_LIMITS['job_matches']} job description matches. Upgrade to PRO for unlimited matches!"
    return True, None


# ── Lightweight in-memory rate limiting ────────────────────────────────────
# Good enough for a single-process deployment; resets on restart.
# For multi-worker deployments swap in Redis-backed counters later.

_rate_lock = threading.Lock()
_rate_buckets = {}


def rate_limit(bucket: str, max_hits: int, window_seconds: int) -> bool:
    """
    Return True when the calling client IP is allowed for this bucket,
    False when it exceeded max_hits within window_seconds.
    """
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    key = f"{bucket}:{ip.split(',')[0].strip()}"
    now = time.time()

    with _rate_lock:
        hits = [t for t in _rate_buckets.get(key, []) if now - t < window_seconds]
        if len(hits) >= max_hits:
            _rate_buckets[key] = hits
            return False
        hits.append(now)
        _rate_buckets[key] = hits
        # Opportunistic cleanup so the dict cannot grow unbounded
        if len(_rate_buckets) > 5000:
            cutoff = now - window_seconds
            for k in list(_rate_buckets.keys()):
                if all(t < cutoff for t in _rate_buckets[k]):
                    del _rate_buckets[k]
        return True


def is_safe_redirect_url(target: str) -> bool:
    """Only allow relative redirects or same-host absolute URLs (open-redirect guard)."""
    if not target:
        return False
    target = target.strip()
    if target.startswith('/') and not target.startswith('//'):
        return True
    ref_host = urlparse(request.host_url).netloc
    parsed = urlparse(target)
    return parsed.scheme in ('http', 'https') and parsed.netloc == ref_host
