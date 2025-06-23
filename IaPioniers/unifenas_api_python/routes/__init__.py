# routes/status_routes.py
from flask import Blueprint, jsonify, current_app
from datetime import datetime

# Cria um Blueprint. O primeiro argumento é o nome do Blueprint, o segundo é o módulo
status_bp = Blueprint('status', __name__)

@status_bp.route('/status', methods=['GET'])
def status():
    # Podemos acessar as variáveis de cache através de current_app.config, se precisarmos
    # Exemplo: total_features = len(current_app.config['FEATURES_CACHE']) if not current_app.config['FEATURES_CACHE'].empty else 0

    return jsonify({"status": "API está online", "timestamp": datetime.now().isoformat()})