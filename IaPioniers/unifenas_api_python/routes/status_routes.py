# routes/status_routes.py
from flask import Blueprint, jsonify, current_app
from datetime import datetime

status_bp = Blueprint('status', __name__, url_prefix='/api/status')

@status_bp.route('/status', methods=['GET'])
def get_status():
    # Acessa os caches carregados na configuração da aplicação
    raw_logs_loaded = current_app.config.get('RAW_LOGS_CACHE') is not None
    features_loaded = current_app.config.get('FEATURES_CACHE') is not None
    risk_scores_loaded = current_app.config.get('RISK_SCORES_CACHE') is not None

    return jsonify({
        "status": "API is running!",
        "cache_status": {
            "raw_logs_loaded": raw_logs_loaded,
            "features_loaded": features_loaded,
            "risk_scores_loaded": risk_scores_loaded
        },
        "timestamp": datetime.now().isoformat()
    })