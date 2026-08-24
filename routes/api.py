"""
API Routes
Auxiliary JSON API endpoints for AJAX interactions.
"""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import Resume, JobMatch

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/resume/<int:resume_id>/ats-score')
@login_required
def get_ats_score(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'resume_id': resume.id,
        'ats_score': resume.ats_score,
        'keyword_score': resume.keyword_score,
        'formatting_score': resume.formatting_score,
        'grammar_score': resume.grammar_score,
        'readability_score': resume.readability_score,
        'analysis': resume.get_analysis_data()
    })
