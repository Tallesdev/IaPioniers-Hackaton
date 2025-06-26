# File: routes/professor_routes.py

from flask import Blueprint, jsonify, request, current_app
import pandas as pd
from datetime import datetime, timedelta
import json
import numpy as np # Importar numpy para tratar NaNs (pd.notna)

professor_bp = Blueprint('professor', __name__, url_prefix='/api/professor')

# Defina o score máximo possível das regras para normalização
# SOMA DOS POINTS_ de evasion_risk_calculator.py
MAX_POSSIBLE_RULE_SCORE = 100 

@professor_bp.route('/dashboard-data', methods=['GET'])
def get_professor_dashboard_data():
    try:
        professor_id = request.args.get('professor_id')
        if not professor_id:
            current_app.logger.warning(f"[{datetime.now()}] Requisição de dashboard sem professor_id.")
            return jsonify({"error": "Parâmetro professor_id é obrigatório"}), 400

        # --- ACESSAR CACHES DO app.config ---
        df_raw_logs_cache = current_app.config.get('RAW_LOGS_CACHE')
        df_risk_scores_cache = current_app.config.get('RISK_SCORES_CACHE')
        df_features_cache = current_app.config.get('FEATURES_CACHE')
        professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')

        if df_raw_logs_cache is None or df_raw_logs_cache.empty or \
           df_risk_scores_cache is None or df_risk_scores_cache.empty or \
           df_features_cache is None or df_features_cache.empty or \
           professor_course_mapping is None or not professor_course_mapping:
            current_app.logger.error(f"[{datetime.now()}] Caches de dados ou mapeamento estão vazios/inválidos no app.config. Verifique o carregamento inicial em app.py.")
            return jsonify({"error": "Dados internos não disponíveis para processamento. Tente carregar novamente os caches."}), 500

        current_app.logger.debug(f"[{datetime.now()}] Conteúdo completo de PROFESSOR_COURSE_MAPPING no config: {professor_course_mapping}")
        current_app.logger.debug(f"[{datetime.now()}] Tentando obter cursos para o professor: '{professor_id}'.")

        professor_courses = professor_course_mapping.get(professor_id)
        
        current_app.logger.info(f"[{datetime.now()}] Cursos BRUTOS obtidos para '{professor_id}' do mapeamento: {professor_courses}")


        if not professor_courses:
            current_app.logger.warning(f"[{datetime.now()}] Professor '{professor_id}' não encontrado no mapeamento ou sem cursos associados.")
            return jsonify({
                "professorNome": professor_id,
                "totalStudents": 0,
                "studentsAtRisk": 0,
                "totalActivities": 0,
                "currentModuleInfo": {},
                "courseSummaries": [],
                "recentActivities": [],
                "evasionRiskCount": 0,
                "studentEvasionList": []
            })

        # --- NORMALIZAÇÃO DE CASE ---
        professor_courses_normalized = [c.upper() for c in professor_courses]
        current_app.logger.info(f"[{datetime.now()}] Cursos NORMALIZADOS para '{professor_id}': {professor_courses_normalized}")

        # --- Determinação do Módulo Atual ---
        current_date = datetime.now()
        current_app.logger.debug(f"[{datetime.now()}] Data atual para determinação do módulo: {current_date.strftime('%Y-%m-%d %H:%M:%S')}")

        modules = [
            {"number": 1, "start": datetime(2025, 3, 3), "end": datetime(2025, 5, 4, 23, 59, 59, 999999), "display_name": "Módulo 1"},
            {"number": 2, "start": datetime(2025, 5, 5), "end": datetime(2025, 6, 28, 23, 59, 59, 999999), "display_name": "Módulo 2"}, 
            {"number": 3, "start": datetime(2025, 6, 29), "end": datetime(2025, 8, 25, 23, 59, 59, 999999), "display_name": "Módulo 3"}, 
            # Adicione mais módulos conforme necessário
        ]

        current_module_info = None
        for module in modules:
            if module["start"] <= current_date <= module["end"]:
                current_module_info = {
                    "module_number": module["number"],
                    "start_date": module["start"],
                    "end_date": module["end"],
                    "display_name": module["display_name"]
                }
                break

        if not current_module_info:
            current_app.logger.info(f"[{datetime.now()}] Nenhum módulo ativo encontrado para a data {current_date.strftime('%Y-%m-%d %H:%M:%S')}. Usando o último módulo como referência.")
            if modules:
                current_module_info = {
                    "module_number": modules[-1]["number"],
                    "start_date": modules[-1]["start"],
                    "end_date": modules[-1]["end"],
                    "display_name": modules[-1]["display_name"]
                }
            else:
                current_app.logger.error(f"[{datetime.now()}] Nenhuma definição de módulo encontrada.")
                return jsonify({"error": "Nenhuma definição de módulo encontrada."}), 500

        current_module_info_start_date = current_module_info["start_date"]
        current_module_info_end_date = current_module_info["end_date"]
        current_app.logger.info(f"[{datetime.now()}] Datas de filtro do módulo ativo: Início={current_module_info_start_date}, Fim={current_module_info_end_date}")

        if not pd.api.types.is_datetime64_any_dtype(df_raw_logs_cache['time_dt']):
             current_app.logger.error(f"[{datetime.now()}] 'time_dt' em df_raw_logs_cache não é datetime. Isso indica um problema no carregamento em app.py.")
             return jsonify({"error": "Erro interno: Formato de data inválido nos logs brutos."}), 500
        
        filtered_logs_by_module = df_raw_logs_cache[
            (df_raw_logs_cache['time_dt'] >= current_module_info_start_date) &
            (df_raw_logs_cache['time_dt'] <= current_module_info_end_date)
        ]
        current_app.logger.info(f"[{datetime.now()}] Logs APÓS FILTRO DE PERÍODO DO MÓDULO ({current_module_info_start_date} a {current_module_info_end_date}): {len(filtered_logs_by_module)} linhas.")

        if 'course_fullname' not in filtered_logs_by_module.columns:
            current_app.logger.error(f"[{datetime.now()}] Coluna 'course_fullname' ausente nos logs filtrados.")
            return jsonify({"error": "Erro interno: Coluna de curso ausente."}), 500

        if 'course_fullname_normalized' not in filtered_logs_by_module.columns:
            filtered_logs_by_module['course_fullname_normalized'] = filtered_logs_by_module['course_fullname'].astype(str).str.upper()

        filtered_logs_for_professor = filtered_logs_by_module[
            filtered_logs_by_module['course_fullname_normalized'].isin(professor_courses_normalized)
        ].copy() 
        current_app.logger.info(f"[{datetime.now()}] Logs APÓS FILTRO DE CURSO DO PROFESSOR: {len(filtered_logs_for_professor)} linhas. (Cursos: {professor_courses_normalized})")

        total_students = filtered_logs_for_professor['user_id'].nunique()
        
        # Filtrar os scores de risco para os cursos do professor
        professor_risk_scores = df_risk_scores_cache[
            df_risk_scores_cache['course_fullname'].str.upper().isin(professor_courses_normalized) # Usar normalized_professor_courses para consistência
        ].copy() # Adicionado .copy() para evitar SettingWithCopyWarning
        current_app.logger.debug(f"[{datetime.now()}] professor_risk_scores (primeiras 5 linhas):\n{professor_risk_scores.head().to_string()}")
        current_app.logger.debug(f"[{datetime.now()}] Contagem de is_at_risk em professor_risk_scores:\n{professor_risk_scores['is_at_risk'].value_counts().to_string()}")


        students_at_risk_df = professor_risk_scores[
            professor_risk_scores['user_id'].isin(filtered_logs_for_professor['user_id'].unique()) &
            professor_risk_scores['is_at_risk'] == 1
        ].copy() # Adicionado .copy()
        students_at_risk = students_at_risk_df['user_id'].nunique()
        current_app.logger.debug(f"[{datetime.now()}] students_at_risk_df (primeiras 5 linhas):\n{students_at_risk_df.head().to_string()}")
        current_app.logger.debug(f"[{datetime.now()}] students_at_risk_df está vazio? {students_at_risk_df.empty}")
        current_app.logger.debug(f"[{datetime.now()}] Total de alunos para {professor_id}: {total_students}, Alunos em risco: {students_at_risk}")

        total_activities = len(filtered_logs_for_professor)

        course_summaries_list = []
        if not filtered_logs_for_professor.empty:
            students_in_course_raw = filtered_logs_for_professor.groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsInCourse')
            
            valid_risk_users = df_risk_scores_cache['user_id'].unique() if not df_risk_scores_cache.empty else []
            valid_feature_users = df_features_cache['user_id'].unique() if not df_features_cache.empty else []

            df_risk_scores_professor_courses = df_risk_scores_cache[
                (df_risk_scores_cache['course_fullname'].isin(professor_courses)) & 
                (df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique())) &
                (df_risk_scores_cache['user_id'].isin(valid_risk_users)) 
            ].copy()
            
            students_at_risk_in_course = df_risk_scores_professor_courses[df_risk_scores_professor_courses['is_at_risk'] == 1] \
                                                .groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsAtRiskInCourse')
            
            df_features_professor_courses = df_features_cache[
                (df_features_cache['course_fullname'].isin(professor_courses)) & 
                (df_features_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique())) &
                (df_features_cache['user_id'].isin(valid_feature_users)) 
            ].copy()

            average_engagement_score_course = df_features_professor_courses.groupby('course_fullname')['engagement_per_day'].mean().reset_index(name='AverageEngagementScore')
            
            last_activity_date_course = filtered_logs_for_professor.groupby('course_fullname')['time_dt'].max().reset_index(name='LastActivityDate')

            all_professor_courses_df = pd.DataFrame(professor_courses, columns=['course_fullname'])

            merged_summaries = pd.merge(all_professor_courses_df, students_in_course_raw, on='course_fullname', how='left').fillna({'StudentsInCourse': 0})
            merged_summaries = pd.merge(merged_summaries, students_at_risk_in_course, on='course_fullname', how='left').fillna({'StudentsAtRiskInCourse': 0})
            merged_summaries = pd.merge(merged_summaries, average_engagement_score_course, on='course_fullname', how='left').fillna({'AverageEngagementScore': 0.0})
            merged_summaries = pd.merge(merged_summaries, last_activity_date_course, on='course_fullname', how='left')

            for _, row in merged_summaries.iterrows():
                course_summaries_list.append({
                    "CourseName": row['course_fullname'],
                    "StudentsInCourse": int(row['StudentsInCourse']),
                    "StudentsAtRiskInCourse": int(row['StudentsAtRiskInCourse']),
                    "AverageEngagementScore": round(row['AverageEngagementScore'], 2),
                    "LastActivityDate": row['LastActivityDate'].isoformat() if pd.notna(row['LastActivityDate']) else "N/A"
                })
        else:
            course_summaries_list = []

        recent_activities_data = [] 
        user_ids_in_module = filtered_logs_for_professor['user_id'].unique() if not filtered_logs_for_professor.empty else []

        if not df_raw_logs_cache.empty and len(user_ids_in_module) > 0: 
            recent_logs_for_display = df_raw_logs_cache[
                df_raw_logs_cache['user_id'].isin(user_ids_in_module) &
                (df_raw_logs_cache['time_dt'] >= current_module_info_start_date) &
                (df_raw_logs_cache['time_dt'] <= current_module_info_end_date)
            ]

            if not recent_logs_for_display.empty:
                recent_logs_for_display = recent_logs_for_display.sort_values(by='time_dt', ascending=False).head(50)

                for _, log in recent_logs_for_display.iterrows():
                    action_info = str(log.get('action', 'Ação Desconhecida')).capitalize()
                    event_info = str(log.get('eventname', 'Evento Desconhecida')).capitalize()
                    target_info = str(log.get('target', '')).capitalize()
                    object_info = str(log.get('object', '')).capitalize()
                    user_name_info = "Desconhecido"
                    if 'user_name' in log and pd.notna(log['user_name']):
                        user_name_info = str(log['user_name'])
                    elif not df_features_cache.empty and 'user_name' in df_features_cache.columns:
                        feature_user_name = df_features_cache[df_features_cache['user_id'] == log['user_id']]['user_name'].iloc[0] if not df_features_cache[df_features_cache['user_id'] == log['user_id']].empty else None
                        if pd.notna(feature_user_name):
                            user_name_info = str(feature_user_name)
                    if user_name_info == "Desconhecido":
                         user_name_info = f"Aluno {log.get('user_id', 'Desconhecido')}"
                    
                    raw_status = log.get('status', None)
                    if raw_status:
                        status_amigavel = str(raw_status).capitalize()
                    else:
                        status_amigavel = "N/A"

                    nome_atividade = "Atividade Desconhecida"
                    if action_info and event_info:
                        nome_atividade = f"{action_info} {event_info}"
                        parts = []
                        if target_info:
                            parts.append(target_info)
                        if object_info:
                            parts.append(object_info)
                        if parts:
                            nome_atividade += f" ({' - '.join(parts)})"
                    elif action_info:
                        nome_atividade = action_info
                    elif event_info:
                        nome_atividade = event_info
                    
                    recent_activities_data.append({
                        "Acao": nome_atividade,
                        "Status": status_amigavel,
                        "DataHora": log['time_dt'].isoformat(),
                        "Usuario": user_name_info
                    })
            else:
                current_app.logger.debug(f"[{datetime.now()}] Nenhum log recente encontrado para exibição no módulo atual.")
        else:
            current_app.logger.debug(f"[{datetime.now()}] Sem dados para atividades recentes (cache vazio ou sem user_ids).")

        current_app.logger.debug(f"[{datetime.now()}] Atividades recentes geradas para {len(recent_activities_data)} atividades.")

        # --- Construindo a StudentEvasionList ---
        student_evasion_list = []
        if not students_at_risk_df.empty: # Usar students_at_risk_df que já está filtrado para o professor e is_at_risk=1
            risk_user_ids = students_at_risk_df['user_id'].unique()

            # Filtrar features apenas para os alunos em risco que pertencem aos cursos do professor
            # E que estão no módulo atual (se aplicável, embora o df_risk_scores_cache já seja global)
            filtered_features_for_risk_students = df_features_cache[
                df_features_cache['user_id'].isin(risk_user_ids) &
                df_features_cache['course_fullname'].str.upper().isin(professor_courses_normalized)
            ].copy()

            current_app.logger.debug(f"[{datetime.now()}] Colunas de students_at_risk_df antes do merge para lista de evasão: {students_at_risk_df.columns.tolist()}")
            current_app.logger.debug(f"[{datetime.now()}] Colunas de filtered_features_for_risk_students antes do merge para lista de evasão: {filtered_features_for_risk_students.columns.tolist()}")

            # As colunas necessárias para o merge e para a saída final
            required_cols_risk = ['user_id', 'course_fullname', 'overall_evasion_score', 'evasion_reasons']
            required_cols_features = ['user_id', 'course_fullname', 'user_name', 'total_actions_global', 'overall_last_access_days_ago'] # Removido days_since_last_valuable_submission_course daqui

            # Verificar se as colunas existem antes de tentar acessá-las
            for col in required_cols_risk:
                if col not in students_at_risk_df.columns:
                    current_app.logger.warning(f"[{datetime.now()}] Coluna '{col}' ausente em students_at_risk_df. Isso pode afetar a lista de evasão.")
            for col in required_cols_features:
                if col not in filtered_features_for_risk_students.columns:
                    current_app.logger.warning(f"[{datetime.now()}] Coluna '{col}' ausente em filtered_features_for_risk_students. Isso pode afetar a lista de evasão.")

            merged_student_data = pd.merge(
                students_at_risk_df, 
                filtered_features_for_risk_students, 
                on=['user_id', 'course_fullname'], 
                how='left',
                suffixes=('_risk', '_features') 
            )
            current_app.logger.debug(f"[{datetime.now()}] Colunas de merged_student_data após o merge para lista de evasão: {merged_student_data.columns.tolist()}")
            current_app.logger.debug(f"[{datetime.now()}] merged_student_data (primeiras 5 linhas):\n{merged_student_data.head().to_string()}")
            current_app.logger.debug(f"[{datetime.now()}] Contagem de linhas em merged_student_data: {len(merged_student_data)}")


            students_at_risk_detailed = merged_student_data.copy()

            students_at_risk_detailed['total_actions_global'] = students_at_risk_detailed['total_actions_global'].fillna(0).astype(int)
            students_at_risk_detailed['overall_last_access_days_ago'] = students_at_risk_detailed['overall_last_access_days_ago'].fillna(0).astype(int)
            
            # --- NOVO: Tratamento condicional para 'days_since_last_valuable_submission_course' ---
            if 'days_since_last_valuable_submission_course' in students_at_risk_detailed.columns:
                students_at_risk_detailed['days_since_last_valuable_submission_course'] = students_at_risk_detailed['days_since_last_valuable_submission_course'].fillna(-1).astype(int)
            else:
                current_app.logger.warning(f"[{datetime.now()}] Coluna 'days_since_last_valuable_submission_course' não encontrada em students_at_risk_detailed. Usando valor padrão para 'daysWithoutAccess'.")
                students_at_risk_detailed['days_since_last_valuable_submission_course'] = -1 # Garante que a coluna exista com um valor padrão
            # --- FIM NOVO ---

            # NOVO CÁLCULO DO RISK SCORE: NORMALIZADO PELAS REGRAS (0-100%)
            students_at_risk_detailed['riskScoreDisplay'] = students_at_risk_detailed['overall_evasion_score'].apply(
                lambda x: min(100, int(round((x / MAX_POSSIBLE_RULE_SCORE) * 100))) if MAX_POSSIBLE_RULE_SCORE > 0 else 0
            )
            current_app.logger.debug(f"[{datetime.now()}] students_at_risk_detailed (primeiras 5 linhas com riskScoreDisplay):\n{students_at_risk_detailed[['user_name_features', 'course_fullname', 'overall_evasion_score', 'riskScoreDisplay']].head().to_string()}")


            def parse_evasion_reasons(reasons):
                if pd.isna(reasons) or reasons is None:
                    return []
                if isinstance(reasons, list):
                    return reasons
                if isinstance(reasons, str):
                    try:
                        parsed = json.loads(reasons.replace("'", "\"")) 
                        if isinstance(parsed, list):
                            return [str(item) for item in parsed]
                    except (json.JSONDecodeError, ValueError):
                        pass
                return [str(reasons)] if str(reasons) else []

            evasion_reasons_col = 'evasion_reasons_risk' if 'evasion_reasons_risk' in students_at_risk_detailed.columns else 'evasion_reasons'
            students_at_risk_detailed[evasion_reasons_col] = students_at_risk_detailed[evasion_reasons_col].apply(parse_evasion_reasons)

            for _, row in students_at_risk_detailed.iterrows():
                student_name = "Desconhecido"
                if 'user_name_features' in row and pd.notna(row['user_name_features']):
                    student_name = str(row['user_name_features'])
                elif 'user_name_risk' in row and pd.notna(row['user_name_risk']): 
                    student_name = str(row['user_name_risk'])
                elif 'user_name' in row and pd.notna(row['user_name']): 
                    student_name = str(row['user_name'])
                else:
                    # CORREÇÃO AQUI: Usar 'user_id' em vez de 'user_id_risk'
                    raw_log_user_name = df_raw_logs_cache[df_raw_logs_cache['user_id'] == row['user_id']]['user_name'].iloc[0] if not df_raw_logs_cache[df_raw_logs_cache['user_id'] == row['user_id']].empty else None
                    if pd.notna(raw_log_user_name) and str(raw_log_user_name).lower() != 'nan':
                        student_name = str(raw_log_user_name)
                    else:
                        # CORREÇÃO AQUI: Usar 'user_id' em vez de 'user_id_risk'
                        student_name = f"Aluno {row.get('user_id', 'Desconhecido')}" 

                reasons_for_student = row[evasion_reasons_col]
                if not reasons_for_student:
                    reasons_for_student = ["Nenhuma razão de regra detectada."]

                # Usar days_since_last_valuable_submission_course ou days_since_last_access_global como fallback
                days_without_access = int(row.get('days_since_last_valuable_submission_course', row.get('overall_last_access_days_ago', -1)))


                student_evasion_list.append({
                    "studentId": str(row['user_id']), # CORREÇÃO AQUI: Era 'user_id_risk'
                    "studentName": student_name,
                    "courseName": str(row['course_fullname']),
                    "totalAccesses": int(row.get('total_actions_global', 0)),
                    "daysWithoutAccess": days_without_access, # Usando o valor tratado
                    "riskScore": int(row['riskScoreDisplay']), 
                    "evasionReasons": reasons_for_student
                })
        current_app.logger.debug(f"[{datetime.now()}] student_evasion_list final gerada para {len(student_evasion_list)} alunos em risco.")
        
        evasion_risk_count = students_at_risk 

        response_data = {
            "professorNome": professor_id,
            "totalStudents": total_students,
            "studentsAtRisk": students_at_risk,
            "totalActivities": total_activities, 
            "currentModuleInfo": {
                "number": current_module_info["module_number"] if current_module_info else None,
                "start_date": current_module_info["start_date"].isoformat() if current_module_info and "start_date" in current_module_info and pd.notna(current_module_info["start_date"]) else None,
                "end_date": current_module_info["end_date"].isoformat() if current_module_info and "end_date" in current_module_info and pd.notna(current_module_info["end_date"]) else None,
                "display_name": current_module_info["display_name"] if current_module_info else None
            },
            "courseSummaries": course_summaries_list,
            "recentActivities": recent_activities_data,
            "evasionRiskCount": evasion_risk_count,
            "studentEvasionList": student_evasion_list
        }

        current_app.logger.debug(f"[{datetime.now()}] Dados de resposta final: {json.dumps(response_data, indent=2, default=str)}")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"[{datetime.now()}] Erro inesperado na função get_professor_dashboard_data: {e}", exc_info=True)
        return jsonify({"error": "Erro interno do servidor Flask", "details": str(e)}), 500

