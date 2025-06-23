# routes/evasion_report_routes.py
from flask import Blueprint, jsonify, current_app
from evasion_reports import get_overall_evasion_report
from datetime import datetime
import pandas as pd # Importar pandas para operar com DataFrames


# Cria um Blueprint para as rotas de relatório de evasão
evasion_report_bp = Blueprint('evasion_report', __name__)

@evasion_report_bp.route('/evasion-report/overall', methods=['GET'])
def overall_evasion_report():
    # Acessa o cache de scores de risco da configuração da aplicação
    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')

    if df_risk_scores_cache is None or df_risk_scores_cache.empty:
        return jsonify({
            "error": "Dados de risco de evasão não disponíveis. Por favor, execute collect_raw_logs.py e process_evasion_data.py"
        }), 500

    # Chama a função de lógica de negócio com o DataFrame de scores de risco
    report = get_overall_evasion_report(current_app.config['RISK_SCORES_CACHE'])
    return jsonify(report)