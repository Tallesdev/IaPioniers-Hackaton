# routes/student_routes.py
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime # Importar datetime para logs
import pandas as pd # Importar pandas para verificar tipos de DataFrame

# >>> ADICIONE ESTA LINHA: IMPORTA A FUNÇÃO get_student_profile_details
from student_profile_generator import get_student_profile_details

# Cria um Blueprint para as rotas de estudante
student_bp = Blueprint('student', __name__, url_prefix='/api/student')

@student_bp.route('/student-profile/<user_id>', methods=['GET'])
def student_profile(user_id):
    current_app.logger.info(f"[{datetime.now()}] Requisição recebida para perfil do aluno: '{user_id}'")

    # Acessa os caches carregados na configuração da aplicação Flask
    df_features_cache = current_app.config.get('FEATURES_CACHE')
    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
    df_raw_logs_cache = current_app.config.get('RAW_LOGS_CACHE')

    current_app.logger.debug(f"[{datetime.now()}] Status dos caches: "
                             f"Raw Logs: {'Carregado' if df_raw_logs_cache is not None and not df_raw_logs_cache.empty else 'Vazio/Não Carregado'}, "
                             f"Features: {'Carregado' if df_features_cache is not None and not df_features_cache.empty else 'Vazio/Não Carregado'}, "
                             f"Risk Scores: {'Carregado' if df_risk_scores_cache is not None and not df_risk_scores_cache.empty else 'Vazio/Não Carregado'}")

    # Verifica se os caches foram carregados e não estão vazios
    if (df_features_cache is None or df_features_cache.empty or
        df_risk_scores_cache is None or df_risk_scores_cache.empty or
        df_raw_logs_cache is None or df_raw_logs_cache.empty):
        current_app.logger.error(f"[{datetime.now()}] Dados de perfil (features, risco ou logs brutos) não disponíveis. "
                                 "Por favor, certifique-se de que collect_raw_logs.py e process_evasion_data.py foram executados e os caches carregados corretamente no app.py.")
        return jsonify({
            "error": "Dados de perfil não disponíveis. Certifique-se de que os dados foram processados e carregados."
        }), 500

    try:
        current_app.logger.debug(f"[{datetime.now()}] Chamando get_student_profile_details para user_id: {user_id}")
        # Chama a função de lógica de negócio para obter o perfil detalhado
        profile = get_student_profile_details(
            user_id,
            df_features_cache,
            df_risk_scores_cache,
            df_raw_logs_cache
        )

        if profile and profile.get("user_name"): # Verifica se um perfil válido foi encontrado e tem nome
            current_app.logger.info(f"[{datetime.now()}] Perfil do aluno '{user_id}' obtido com sucesso.")
            return jsonify(profile)
        else:
            current_app.logger.warning(f"[{datetime.now()}] Perfil do aluno com ID '{user_id}' não encontrado ou dados incompletos. Retornando 404.")
            # Retorna 404 se o aluno não for encontrado nos caches
            return jsonify({"message": f"Perfil do aluno com ID '{user_id}' não encontrado ou dados incompletos nos caches."}), 404

    except Exception as e:
        current_app.logger.exception(f"[{datetime.now()}] Ocorreu um erro inesperado ao gerar o perfil para o aluno '{user_id}'.")
        return jsonify({"error": "Erro interno ao processar o perfil do aluno", "details": str(e)}), 500

