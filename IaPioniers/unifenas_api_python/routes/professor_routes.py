# File: routes/professor_routes.py

from flask import Blueprint, jsonify, request, current_app
import pandas as pd
from datetime import datetime, timedelta, date
import json
from academic_calendar_utils import get_module_info_by_fixed_dates

professor_bp = Blueprint('professor', __name__, url_prefix='/api/professor')

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

        professor_courses = professor_course_mapping.get(professor_id)
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

        # --- Determinação do Módulo Atual usando academic_calendar_utils ---
        # Definindo a data atual como uma data dentro do Módulo 2 de 2025 para teste/apresentação.
        current_date = datetime(2025, 6, 15).date() # Use .date() para compatibilidade
        # current_date = date.today() # Para usar a data atual

        current_app.logger.debug(f"[{datetime.now()}] Data de referência para determinação do módulo: {current_date.strftime('%Y-%m-%d')}")

        current_module_info_raw = get_module_info_by_fixed_dates(current_date)

        if not current_module_info_raw:
            current_app.logger.warning(f"[{datetime.now()}] Nenhum módulo encontrado para a data {current_date.strftime('%Y-%m-%d')}. Verifique as definições em academic_calendar.py.")
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
        
        current_module_info_start_date = datetime.combine(current_module_info_raw["start_date"], datetime.min.time())
        current_module_info_end_date = datetime.combine(current_module_info_raw["end_date"], datetime.max.time())

        current_module_info = {
            "module_number": current_module_info_raw["module_number"],
            "start_date": current_module_info_start_date,
            "end_date": current_module_info_end_date,
            "display_name": current_module_info_raw["display_name"] if "display_name" in current_module_info_raw else f"Módulo {current_module_info_raw['module_number']}"
        }

        current_app.logger.info(f"[{datetime.now()}] Datas de filtro do módulo ativo: Início={current_module_info_start_date}, Fim={current_module_info_end_date}")

        # --- Lógica de Filtro e Cálculo de Métricas ---
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

        filtered_logs_for_professor = filtered_logs_by_module[
            filtered_logs_by_module['course_fullname'].isin(professor_courses)
        ].copy() 
        current_app.logger.info(f"[{datetime.now()}] Logs APÓS FILTRO DE CURSO DO PROFESSOR: {len(filtered_logs_for_professor)} linhas. (Cursos: {professor_courses})")

        # --- Cálculos Principais ---
        total_students = filtered_logs_for_professor['user_id'].nunique()
        
        students_at_risk_df_filtered = df_risk_scores_cache[
            (df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique().tolist())) &
            (df_risk_scores_cache['is_at_risk'] == 1)
        ]
        students_at_risk = students_at_risk_df_filtered['user_id'].nunique()
        current_app.logger.debug(f"[{datetime.now()}] Total de alunos para {professor_id}: {total_students}, Alunos em risco: {students_at_risk}")

        total_activities = len(filtered_logs_for_professor)

        # --- Resumo por Curso ---
        course_summaries_list = []
        if not filtered_logs_for_professor.empty:
            students_in_course_raw = filtered_logs_for_professor.groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsInCourse')
            
            valid_risk_users = df_risk_scores_cache['user_id'].unique().tolist() if not df_risk_scores_cache.empty else []
            valid_feature_users = df_features_cache['user_id'].unique().tolist() if not df_features_cache.empty else []

            df_risk_scores_professor_courses = df_risk_scores_cache[
                (df_risk_scores_cache['course_fullname'].isin(professor_courses)) &
                (df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique().tolist())) &
                (df_risk_scores_cache['user_id'].isin(valid_risk_users)) 
            ].copy()
            
            students_at_risk_in_course = df_risk_scores_professor_courses[df_risk_scores_professor_courses['is_at_risk'] == 1] \
                                             .groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsAtRiskInCourse')
            
            df_features_professor_courses = df_features_cache[
                (df_features_cache['course_fullname'].isin(professor_courses)) &
                (df_features_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique().tolist())) &
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

        # --- Atividades Recentes ---
        recent_activities_data = []
        user_ids_in_module = filtered_logs_for_professor['user_id'].unique().tolist() if not filtered_logs_for_professor.empty else []

        if not df_raw_logs_cache.empty and len(user_ids_in_module) > 0: 
            recent_logs_for_display = df_raw_logs_cache[
                df_raw_logs_cache['user_id'].isin(user_ids_in_module) &
                (df_raw_logs_cache['time_dt'] >= current_module_info_start_date) &
                (df_raw_logs_cache['time_dt'] <= current_module_info_end_date)
            ]

            if not recent_logs_for_display.empty:
                recent_logs_for_display = recent_logs_for_display.sort_values(by='time_dt', ascending=False).head(50)

                for _, log in recent_logs_for_display.iterrows():
                    action_info = log.get('action', 'Ação Desconhecida').capitalize()
                    target_info = log.get('target', '').capitalize()
                    user_name_info = str(log.get('user_name', log.get('user_id', 'Desconhecido'))) 

                    if target_info:
                        nome_atividade = f"{action_info} {target_info}"
                    else:
                        nome_atividade = action_info
                    
                    status_amigavel = "N/A" 
                    if action_info == "Graded":
                        status_amigavel = "Concluída" 
                    elif action_info == "Submitted":
                        status_amigavel = "Submetida"
                    elif action_info == "Started":
                        status_amigavel = "Em Andamento"
                    
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

        # --- CALCULAR EVASION RISK COUNT E STUDENT EVASION LIST POR CURSO ---
        evasion_risk_count = 0 # Inicializa como 0, será calculado por curso
        student_evasion_list = []

        if not df_risk_scores_cache.empty and not df_features_cache.empty:
            # Filtra scores de risco e features para os cursos do professor e alunos logados no módulo
            risk_scores_for_professor_courses = df_risk_scores_cache[
                df_risk_scores_cache['course_fullname'].isin(professor_courses) &
                df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique().tolist())
            ].copy()

            features_for_professor_courses = df_features_cache[
                df_features_cache['course_fullname'].isin(professor_courses) &
                df_features_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique().tolist())
            ].copy()
            
            # Atualiza evasion_risk_count com base nos alunos em risco filtrados
            evasion_risk_count = risk_scores_for_professor_courses[risk_scores_for_professor_courses['is_at_risk'] == 1]['user_id'].nunique()

            # Junta os dados de risco e features para calcular as métricas por aluno E por curso
            # Se um aluno está em múltiplos cursos e tem risco, ele aparecerá múltiplas vezes aqui.
            merged_evasion_data_per_course = pd.merge(
                risk_scores_for_professor_courses[['user_id', 'user_name', 'course_fullname', 'evasion_probability_ml', 'is_at_risk']],
                features_for_professor_courses[['user_id', 'course_fullname', 'overall_last_access_days_ago', 'course_activity_count']],
                on=['user_id', 'course_fullname'], # Chave de junção dupla
                how='inner' 
            )
            
            # Filtra apenas os alunos em risco para a lista de exibição
            students_at_risk_per_course_for_list = merged_evasion_data_per_course[
                merged_evasion_data_per_course['is_at_risk'] == 1
            ]

            if not students_at_risk_per_course_for_list.empty:
                # Ordena pela probabilidade de evasão (desc) e depois pelo nome do aluno
                students_at_risk_per_course_for_list = students_at_risk_per_course_for_list.sort_values(
                    by=['evasion_probability_ml', 'user_name'], ascending=[False, True]
                )

                for _, student_row in students_at_risk_per_course_for_list.iterrows():
                    student_evasion_list.append({
                        "StudentName": student_row['user_name'],
                        "CourseName": student_row['course_fullname'], # Agora inclui o nome do curso
                        "TotalAccesses": int(student_row['course_activity_count']), # Acessos DENTRO DESTE CURSO
                        "DaysWithoutAccess": int(student_row['overall_last_access_days_ago']), # Dias sem acesso (geral, ou adaptar se precisar por curso)
                        "EvasionProbability": int(round(student_row['evasion_probability_ml'] * 100))
                    })
        
        current_app.logger.debug(f"[{datetime.now()}] Alunos em risco para lista de evasão (por curso): {len(student_evasion_list)}")

        # --- Prepara e Retorna a resposta JSON final ---
        response_data = {
            "professorNome": professor_id,
            "totalStudents": total_students,
            "studentsAtRisk": students_at_risk,
            "totalActivities": total_activities, 
            "currentModuleInfo": {
                "number": current_module_info["module_number"],
                "start_date": current_module_info["start_date"].isoformat(),
                "end_date": current_module_info["end_date"].isoformat(),
                "display_name": current_module_info["display_name"]
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
