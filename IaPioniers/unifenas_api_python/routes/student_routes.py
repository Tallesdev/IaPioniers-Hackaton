# routes/student_routes.py
from flask import Blueprint, jsonify, current_app, request
from student_profile_generator import get_student_profile_details

# Cria um Blueprint para as rotas de estudante
student_bp = Blueprint('student', __name__)

@student_bp.route('/student-profile/<user_id>', methods=['GET'])
def student_profile(user_id):
    # Acessa os caches carregados na configuração da aplicação Flask
    df_features_cache = current_app.config.get('FEATURES_CACHE')
    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
    df_raw_logs_cache = current_app.config.get('RAW_LOGS_CACHE') # Este é o DataFrame de logs brutos

    # Verifica se os caches foram carregados
    if (df_features_cache is None or df_features_cache.empty or
        df_risk_scores_cache is None or df_risk_scores_cache.empty or
        df_raw_logs_cache is None or df_raw_logs_cache.empty):
        return jsonify({
            "error": "Dados de perfil (features, risco ou logs brutos) não disponíveis. Por favor, certifique-se de que collect_raw_logs.py e process_evasion_data.py foram executados e os caches carregados."
        }), 500

    # Chama a função de lógica de negócio para obter o perfil detalhado
    # Passando os três DataFrames necessários como argumentos separados
    profile = get_student_profile_details(
        user_id,
        df_features_cache,
        df_risk_scores_cache,
        df_raw_logs_cache # Passando o DataFrame de logs brutos aqui
    )

    if profile and profile.get("user_name"): # Verifica se um perfil válido foi encontrado e tem nome
        return jsonify(profile)
    else:
        # Retorna 404 se o aluno não for encontrado nos caches
        return jsonify({"message": f"Perfil do aluno com ID '{user_id}' não encontrado ou dados incompletos nos caches."}), 404