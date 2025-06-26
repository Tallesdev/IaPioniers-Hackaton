# routes/course_routes.py (ou no seu app.py, se preferir organizar assim)

from flask import Blueprint, jsonify, current_app
from datetime import datetime

course_bp = Blueprint('course', __name__, url_prefix='/api/courses')

@course_bp.route('/all-names', methods=['GET'])
def get_all_course_names():
    try:
        df_raw_logs_cache = current_app.config.get('RAW_LOGS_CACHE')

        if df_raw_logs_cache is None or df_raw_logs_cache.empty:
            current_app.logger.error(f"[{datetime.now()}] RAW_LOGS_CACHE está vazio/inválido no app.config. Verifique o carregamento inicial em app.py.")
            return jsonify({"error": "Dados de log brutos não disponíveis."}), 500

        if 'course_fullname' not in df_raw_logs_cache.columns:
            current_app.logger.error(f"[{datetime.now()}] Coluna 'course_fullname' ausente no df_raw_logs_cache.")
            return jsonify({"error": "Erro interno: Coluna de curso ausente nos logs brutos."}), 500

        # Pega todos os nomes de curso únicos do cache de logs brutos
        # Converte para string e depois para maiúsculas para normalização, assim como no dashboard
        unique_course_names = df_raw_logs_cache['course_fullname'].astype(str).str.upper().unique().tolist()
        
        current_app.logger.info(f"[{datetime.now()}] Retornando {len(unique_course_names)} nomes de cursos únicos.")
        return jsonify({"courseNames": unique_course_names})

    except Exception as e:
        current_app.logger.error(f"[{datetime.now()}] Erro inesperado na função get_all_course_names: {e}", exc_info=True)
        return jsonify({"error": "Erro interno do servidor Flask", "details": str(e)}), 500

