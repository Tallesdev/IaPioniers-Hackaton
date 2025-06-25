# routes/evasion_report_routes.py

from flask import Blueprint, jsonify, current_app, request # Garanta que 'request' esteja aqui
import pandas as pd # Certifique-se de que pandas está importado
from datetime import datetime # Certifique-se de que datetime está importado
from evasion_reports import get_overall_evasion_report # Mantém esta importação para o endpoint /overall

# Cria um Blueprint para as rotas de relatório de evasão
evasion_report_bp = Blueprint('evasion_report', __name__, url_prefix='/api/evasion-report')


@evasion_report_bp.route('/evasion-report/overall', methods=['GET'])
def overall_evasion_report():
    """
    Retorna um relatório geral de evasão.
    """
    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')

    if df_risk_scores_cache is None or df_risk_scores_cache.empty:
        current_app.logger.error(f"[{datetime.now()}] Dados de risco de evasão não disponíveis no cache para /evasion-report/overall.")
        return jsonify({
            "error": "Dados de risco de evasão não disponíveis. Por favor, certifique-se de que os caches foram carregados."
        }), 500

    report = get_overall_evasion_report(df_risk_scores_cache)
    return jsonify(report)


@evasion_report_bp.route('/evasion-report/at-risk-students', methods=['GET'])
def get_at_risk_students(): # Renomeei para ser consistente com o nome do arquivo, mas a rota é a mesma
    """
    Retorna uma lista de alunos em risco de evasão, filtrada por professor_id e/ou course_name.
    """
    professor_id = request.args.get('professor_id')
    course_name = request.args.get('course_name')

    df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
    df_features_cache = current_app.config.get('FEATURES_CACHE')
    professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')

    # Validação de caches
    if df_risk_scores_cache is None or df_risk_scores_cache.empty:
        current_app.logger.error(f"[{datetime.now()}] Dados de risco de evasão não disponíveis no cache (RISK_SCORES_CACHE).")
        return jsonify({"error": "Dados de risco de evasão não disponíveis no cache."}), 500
    if df_features_cache is None or df_features_cache.empty:
        current_app.logger.error(f"[{datetime.now()}] Dados de features de alunos não disponíveis no cache (FEATURES_CACHE).")
        return jsonify({"error": "Dados de features de alunos não disponíveis no cache."}), 500
    if professor_course_mapping is None:
        current_app.logger.error(f"[{datetime.now()}] Mapeamento de professor-curso não carregado (PROFESSOR_COURSE_MAPPING).")
        return jsonify({"error": "Mapeamento de professor-curso não carregado."}), 500

    # Validação de colunas essenciais
    if 'is_at_risk' not in df_risk_scores_cache.columns:
        current_app.logger.error(f"[{datetime.now()}] Coluna 'is_at_risk' não encontrada em RISK_SCORES_CACHE.")
        return jsonify({"error": "Formato inválido dos dados de risco: coluna 'is_at_risk' ausente."}), 500
    if 'user_id' not in df_risk_scores_cache.columns or 'user_id' not in df_features_cache.columns:
        current_app.logger.error(f"[{datetime.now()}] Coluna 'user_id' ausente em um dos DataFrames (risk_data ou features_cache).")
        return jsonify({"error": "Dados inconsistentes: coluna 'user_id' ausente."}), 500
    if 'user_name' not in df_features_cache.columns:
        current_app.logger.error(f"[{datetime.now()}] Coluna 'user_name' ausente em FEATURES_CACHE.")
        return jsonify({"error": "Dados inconsistentes: coluna 'user_name' ausente em features."}), 500
    if 'overall_evasion_score' not in df_risk_scores_cache.columns:
        current_app.logger.error(f"[{datetime.now()}] Coluna 'overall_evasion_score' não encontrada em RISK_SCORES_CACHE.")
        return jsonify({"error": "Formato inválido dos dados de risco: coluna 'overall_evasion_score' ausente."}), 500
    if 'course_fullname' not in df_risk_scores_cache.columns:
        current_app.logger.error(f"[{datetime.now()}] Coluna 'course_fullname' não encontrada em RISK_SCORES_CACHE.")
        return jsonify({"error": "Formato inválido dos dados de risco: coluna 'course_fullname' ausente."}), 500


    # Filtra apenas os alunos que estão em risco
    filtered_risk_data = df_risk_scores_cache[df_risk_scores_cache['is_at_risk'] == True].copy()
    
    # Aplica filtro por professor_id
    if professor_id:
        prof_courses = professor_course_mapping.get(professor_id, [])
        if not prof_courses:
            current_app.logger.info(f"[{datetime.now()}] Nenhum curso encontrado para o professor {professor_id} no mapeamento. Retornando vazio.")
            return jsonify({"message": f"Nenhum aluno em risco encontrado para o professor {professor_id} com os cursos mapeados."}), 200
        
        filtered_risk_data = filtered_risk_data[filtered_risk_data['course_fullname'].isin(prof_courses)]
    
    # Aplica filtro por course_name (se houver, e após o filtro por professor, se aplicável)
    if course_name:
        filtered_risk_data = filtered_risk_data[filtered_risk_data['course_fullname'] == course_name].copy()
        
    # Se não houver dados após os filtros
    if filtered_risk_data.empty:
        current_app.logger.info(f"[{datetime.now()}] Nenhum aluno em risco encontrado com os critérios fornecidos (professor_id: {professor_id}, course_name: {course_name}).")
        return jsonify({"message": "Nenhum aluno em risco encontrado com os critérios fornecidos."}), 200

    # Realiza o merge para obter o nome do aluno
    at_risk_students_details = pd.merge(
        filtered_risk_data[['user_id', 'overall_evasion_score', 'course_fullname', 'evasion_reasons']],
        df_features_cache[['user_id', 'user_name']].drop_duplicates(subset=['user_id']),
        on='user_id',
        how='left'
    )

    # Formata a saída
    output = []
    for index, row in at_risk_students_details.iterrows():
        student_name = row['user_name'] if pd.notna(row['user_name']) else f"Aluno {row['user_id']}"
        
        # Lida com 'evasion_reasons'
        evasion_reasons = row.get('evasion_reasons')
        if pd.isna(evasion_reasons):
            evasion_reasons = []
        elif isinstance(evasion_reasons, str):
            try:
                # Tenta avaliar strings que parecem listas (ex: "['motivo1', 'motivo2']")
                parsed_reasons = eval(evasion_reasons)
                if isinstance(parsed_reasons, list):
                    evasion_reasons = parsed_reasons
                else:
                    evasion_reasons = [str(evasion_reasons)]
            except (SyntaxError, NameError):
                evasion_reasons = [str(evasion_reasons)] # Se falhar, trata como uma única string
        elif not isinstance(evasion_reasons, list):
            evasion_reasons = [str(evasion_reasons)] # Garante que é uma lista de strings

        output.append({
            "studentId": str(row['user_id']), # Garante que o ID é string
            "studentName": student_name,
            "courseName": row['course_fullname'],
            "riskScore": round(float(row['overall_evasion_score']), 4), # Garante que é float e arredonda
            "evasionReasons": evasion_reasons
        })

    current_app.logger.info(f"[{datetime.now()}] Encontrados {len(output)} alunos em risco para (professor_id: {professor_id}, course_name: {course_name}).")
    return jsonify({"atRiskStudents": output})