# routes/students_overview_routes.py

from flask import Blueprint, jsonify, request, current_app
import pandas as pd
from datetime import datetime, timedelta
import json
import numpy as np

# Cria um Blueprint para as rotas de visão geral de alunos
students_overview_bp = Blueprint('students_overview', __name__, url_prefix='/api/students-overview')

@students_overview_bp.route('/list', methods=['GET'])
def get_students_overview_list():
    try:
        professor_id = request.args.get('professor_id')
        course_name_filter = request.args.get('course_name') # Opcional: filtro por curso

        if not professor_id:
            current_app.logger.warning(f"[{datetime.now()}] Requisição de lista de alunos sem professor_id.")
            return jsonify({"error": "Parâmetro professor_id é obrigatório"}), 400

        # Acessar caches
        df_raw_logs_cache = current_app.config.get('RAW_LOGS_CACHE')
        df_features_cache = current_app.config.get('FEATURES_CACHE')
        df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
        professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')

        if df_raw_logs_cache is None or df_raw_logs_cache.empty or \
           df_features_cache is None or df_features_cache.empty or \
           df_risk_scores_cache is None or df_risk_scores_cache.empty or \
           professor_course_mapping is None or not professor_course_mapping:
            current_app.logger.error(f"[{datetime.now()}] Caches de dados ou mapeamento estão vazios/inválidos para a lista de alunos.")
            return jsonify({"error": "Dados internos não disponíveis para processamento da lista de alunos. Tente carregar novamente os caches."}), 500

        professor_courses = professor_course_mapping.get(professor_id)
        if not professor_courses:
            current_app.logger.warning(f"[{datetime.now()}] Professor '{professor_id}' não encontrado no mapeamento ou sem cursos associados.")
            return jsonify({"students": [], "message": f"Nenhum curso associado ao professor '{professor_id}'."})

        professor_courses_normalized = [c.upper() for c in professor_courses]

        # Filtrar logs para os cursos do professor
        if 'course_fullname_normalized' not in df_raw_logs_cache.columns:
            df_raw_logs_cache['course_fullname_normalized'] = df_raw_logs_cache['course_fullname'].astype(str).str.upper()

        filtered_logs_for_professor_courses = df_raw_logs_cache[
            df_raw_logs_cache['course_fullname_normalized'].isin(professor_courses_normalized)
        ].copy()

        # Filtrar features para os cursos do professor
        if 'course_fullname_normalized' not in df_features_cache.columns:
            df_features_cache['course_fullname_normalized'] = df_features_cache['course_fullname'].astype(str).str.upper()
        
        filtered_features_for_professor = df_features_cache[
            df_features_cache['course_fullname_normalized'].isin(professor_courses_normalized)
        ].copy()

        # Aplicar filtro adicional por course_name_filter, se fornecido
        if course_name_filter:
            course_name_filter_normalized = course_name_filter.upper()
            filtered_logs_for_professor_courses = filtered_logs_for_professor_courses[
                filtered_logs_for_professor_courses['course_fullname_normalized'] == course_name_filter_normalized
            ].copy()
            filtered_features_for_professor = filtered_features_for_professor[
                filtered_features_for_professor['course_fullname_normalized'] == course_name_filter_normalized
            ].copy()
            current_app.logger.info(f"[{datetime.now()}] Filtro de curso aplicado: {course_name_filter_normalized}. Logs: {len(filtered_logs_for_professor_courses)} Features: {len(filtered_features_for_professor)}")

        # Obter IDs de alunos únicos neste contexto
        relevant_user_ids = filtered_logs_for_professor_courses['user_id'].unique()
        if len(relevant_user_ids) == 0:
            return jsonify({"students": [], "message": "Nenhum aluno encontrado para os cursos do professor no período atual."})

        # Filtrar os DataFrames de features e risco apenas para os alunos relevantes
        relevant_features = filtered_features_for_professor[
            filtered_features_for_professor['user_id'].isin(relevant_user_ids)
        ].copy()

        relevant_risk_scores = df_risk_scores_cache[
            df_risk_scores_cache['user_id'].isin(relevant_user_ids)
        ].copy()
        
        # Juntar features com scores de risco para ter todas as informações
        # Fazemos um outer merge para garantir que pegamos todos os alunos relevantes,
        # mesmo que não tenham risco calculado.
        students_data = pd.merge(
            relevant_features,
            relevant_risk_scores[['user_id', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']],
            on=['user_id', 'course_fullname'],
            how='left'
        )

        # Tratar NaNs após o merge (para alunos que podem não ter score de risco)
        students_data['overall_evasion_score'] = students_data['overall_evasion_score'].fillna(0).astype(int)
        students_data['is_at_risk'] = students_data['is_at_risk'].fillna(0).astype(int)
        students_data['evasion_reasons'] = students_data['evasion_reasons'].fillna("Nenhuma razão detectada pelas regras.").astype(str)
        
        # Garantir que as colunas existem antes de tentar acessá-las e preencher NaNs
        if 'days_since_last_valuable_submission_course' in students_data.columns:
            students_data['days_since_last_valuable_submission_course'] = students_data['days_since_last_valuable_submission_course'].fillna(-1).astype(int)
        else:
            students_data['days_since_last_valuable_submission_course'] = -1 # Adiciona a coluna com valor padrão se não existir

        if 'total_submissions_course' in students_data.columns:
            students_data['total_submissions_course'] = students_data['total_submissions_course'].fillna(0).astype(int)
        else:
            students_data['total_submissions_course'] = 0 # Adiciona a coluna com valor padrão se não existir


        # Preparar a lista de alunos para a resposta JSON
        students_list_for_response = []
        for _, row in students_data.iterrows():
            student_name = row.get('user_name') if pd.notna(row.get('user_name')) else f"Aluno {row['user_id']}"
            course_name = row.get('course_fullname', 'Curso Desconhecido')
            
            # --- Lógica para o Status do Aluno ---
            status = "Participando"
            status_details = []

            # Prioridade: Inativo > Atrasado > Participando
            # Usar os thresholds configurados no app.py
            if 'days_since_last_access_global' in row and pd.notna(row['days_since_last_access_global']) and \
               row['days_since_last_access_global'] >= current_app.config['INACTIVITY_THRESHOLD_GLOBAL_DAYS_CONFIG']:
                status = "Inativo"
                status_details.append(f"Inativo (último acesso global há {row['days_since_last_access_global']} dias)")
            elif 'days_since_last_access_course' in row and pd.notna(row['days_since_last_access_course']) and \
                 row['days_since_last_access_course'] >= current_app.config['INACTIVITY_THRESHOLD_COURSE_DAYS_CONFIG']:
                 status = "Inativo" # Ou "Inativo no Curso" se quiser granularidade
                 status_details.append(f"Inativo no curso ({course_name}, último acesso há {row['days_since_last_access_course']} dias)") # CORRIGIDO AQUI
            elif 'overall_evasion_score' in row and pd.notna(row['overall_evasion_score']) and \
                 row['overall_evasion_score'] >= current_app.config['DEFAULT_RISK_THRESHOLD_CONFIG']:
                status = "Atrasado" # Ou "Em Risco"
                status_details.append(f"Em risco de evasão (score de regras: {row['overall_evasion_score']}%)")
                if row['evasion_reasons'] and row['evasion_reasons'] != "Nenhuma razão detectada pelas regras.":
                    reasons_list = []
                    if isinstance(row['evasion_reasons'], str):
                        try:
                            # Tenta carregar como JSON (se for string de lista)
                            parsed_reasons = json.loads(row['evasion_reasons'].replace("'", "\""))
                            if isinstance(parsed_reasons, list):
                                reasons_list.extend(parsed_reasons)
                            else:
                                reasons_list.append(str(row['evasion_reasons']))
                        except json.JSONDecodeError:
                            reasons_list.append(str(row['evasion_reasons']))
                    elif isinstance(row['evasion_reasons'], list):
                        reasons_list.extend(row['evasion_reasons'])
                    else:
                        reasons_list.append(str(row['evasion_reasons']))
                    
                    status_details.append(f"Motivos: {'; '.join(reasons_list)}")
            elif 'total_actions_global' in row and pd.notna(row['total_actions_global']) and row['total_actions_global'] < 50: # Exemplo: poucas ações globais
                status = "Atrasado"
                status_details.append("Baixa interação global (<50 ações)")
            elif 'course_total_actions' in row and pd.notna(row['course_total_actions']) and row['course_total_actions'] < 10: # Exemplo: poucas ações no curso
                status = "Atrasado"
                status_details.append(f"Baixa interação no curso ({course_name}, <10 ações)")

            # --- Lógica para Entrega Recente ---
            recent_submission = "Nenhuma Entrega Recente"
            if 'total_submissions_course' in row and pd.notna(row['total_submissions_course']) and row['total_submissions_course'] > 0:
                if 'days_since_last_valuable_submission_course' in row and pd.notna(row['days_since_last_valuable_submission_course']) and \
                   row['days_since_last_valuable_submission_course'] != -1:
                    recent_submission = f"Última entrega há {row['days_since_last_valuable_submission_course']} dias."
                else:
                    recent_submission = "Entrega(s) registrada(s), data desconhecida."
            
            students_list_for_response.append({
                "studentId": str(row['user_id']),
                "studentName": student_name,
                "courseName": course_name,
                "status": status,
                "statusDetails": status_details,
                "recentSubmission": recent_submission
            })

        current_app.logger.info(f"[{datetime.now()}] Retornando {len(students_list_for_response)} alunos para {professor_id}.")
        return jsonify({"students": students_list_for_response})

    except Exception as e:
        current_app.logger.error(f"[{datetime.now()}] Erro inesperado na função get_students_overview_list: {e}", exc_info=True)
        return jsonify({"error": "Erro interno do servidor Flask", "details": str(e)}), 500
