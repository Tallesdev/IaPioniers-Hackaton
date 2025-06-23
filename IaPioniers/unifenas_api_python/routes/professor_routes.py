# routes/professor_routes.py
from flask import Blueprint, jsonify, request, current_app
from evasion_reports import get_evasion_risk_students_for_professor
from datetime import datetime

professor_bp = Blueprint('professor', __name__)

@professor_bp.route('/professor-evasion-risk', methods=['GET'])
def professor_evasion_risk():
    professor_id = request.args.get('professor_id')
    course_name = request.args.get('course_name')

    if not professor_id and not course_name:
        return jsonify({"error": "Por favor, forneça 'professor_id' ou 'course_name' como parâmetro de consulta."}), 400

    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
    df_features_cache = current_app.config.get('FEATURES_CACHE') 

    if (df_risk_scores_cache is None or df_risk_scores_cache.empty or
        df_features_cache is None or df_features_cache.empty):
        return jsonify({
            "error": "Dados de risco de evasão ou features não disponíveis. Por favor, execute collect_raw_logs.py e process_evasion_data.py"
        }), 500
    
    professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')
    if professor_id and not professor_course_mapping:
        return jsonify({
            "error": "Mapeamento professor-curso não disponível. Não é possível filtrar por professor_id sem 'professor_curso_mapping.json'."
        }), 500

    risky_students_report = get_evasion_risk_students_for_professor(
        df_risk_scores_cache,
        df_features_cache, 
        professor_id,
        course_name
    )
    return jsonify(risky_students_report)
@professor_bp.route('/professor/course-summaries', methods=['GET'])
def get_professor_course_summaries():
    professor_name = request.args.get('professor_id')
    current_app.logger.debug(f"Professor ID recebido (raw): {professor_name}")
    print(f"DEBUG: Professor solicitado: {professor_name}")

    if not professor_name:
        return jsonify({"error": "O parâmetro 'professor_id' (nome do professor) é obrigatório."}), 400

    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
    df_features_cache = current_app.config.get('FEATURES_CACHE')
    professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')

    if (df_risk_scores_cache is None or df_risk_scores_cache.empty or
        df_features_cache is None or df_features_cache.empty or
        professor_course_mapping is None or not professor_course_mapping):
        return jsonify({
            "error": "Dados ou mapeamento de professor-curso não disponíveis nos caches. Verifique se os caches foram carregados e o 'professor_course_mapping.json' está presente e no formato correto."
        }), 500

    course_summaries = []
    
    # Certifique-se de que a chave existe e que o valor é uma lista.
    # professor_name pode vir com acentuação ou caixa diferente, então normalizar é bom
    # No entanto, vamos assumir que o professor_course_mapping já tem a chave exata
    # Para fins de teste, você pode querer printar professor_course_mapping.keys() aqui.
    courses_for_professor = professor_course_mapping.get(professor_name, [])
    print(f"DEBUG: Cursos mapeados para {professor_name}: {courses_for_professor}")

    if not df_features_cache.empty:
        print(f"DEBUG: Nomes de curso únicos em df_features_cache: {df_features_cache['course_fullname'].unique()}")
    if not df_risk_scores_cache.empty:
        print(f"DEBUG: Nomes de curso únicos em df_risk_scores_cache: {df_risk_scores_cache['course_fullname'].unique()}")
    
    for course_name_identifier in courses_for_professor:
        print(f"DEBUG: Processando curso: {course_name_identifier}")
        
        students_in_course_df = df_features_cache[
            (df_features_cache['course_fullname'] == course_name_identifier)
        ]
        total_students_in_course = len(students_in_course_df)

        risky_students_df = df_risk_scores_cache[
            (df_risk_scores_cache['course_fullname'] == course_name_identifier) &
            # CORREÇÃO AQUI: Use 'is_at_risk' ou 'evasion_probability_ml'
            (df_risk_scores_cache['is_at_risk'] == 1) # Usando o indicador binário do rule-based
            # OU se preferir o ML: (df_risk_scores_cache['evasion_probability_ml'] > 0.5)
            # OU se preferir o score de regras: (df_risk_scores_cache['overall_evasion_score'] >= SEU_THRESHOLD_AQUI)
        ]
        students_at_risk_in_course = len(risky_students_df)

        print(f"DEBUG: Curso '{course_name_identifier}': Total de alunos: {total_students_in_course}, Alunos em risco: {students_at_risk_in_course}")

        course_summaries.append({
            "CourseName": course_name_identifier,
            "StudentsInCourse": total_students_in_course,
            "StudentsAtRiskInCourse": students_at_risk_in_course,
            "LastActivityDate": None, # Ainda sem implementação para esta feature
            "AverageEngagementScore": None # Ainda sem implementação para esta feature
        })
    
    print(f"DEBUG: Resumo final dos cursos: {course_summaries}")
    return jsonify(course_summaries)