# File: routes/professor_routes.py

from flask import Blueprint, jsonify, request, current_app
import pandas as pd
from datetime import datetime, timedelta
import json
# Importar os para acesso aos caminhos se você não usa app.config para eles aqui
# import os 

professor_bp = Blueprint('professor', __name__, url_prefix='/api/professor')

# REMOVA A FUNÇÃO load_caches_for_testing() COMPLETAMENTE DAQUI.
# Ela causou confusão e erros de caminho.

@professor_bp.route('/dashboard-data', methods=['GET'])
def get_professor_dashboard_data():
    try:
        professor_id = request.args.get('professor_id')
        if not professor_id:
            current_app.logger.warning(f"[{datetime.now()}] Requisição de dashboard sem professor_id.")
            return jsonify({"error": "Parâmetro professor_id é obrigatório"}), 400

        # --- ACESSAR CACHES DO app.config ---
        # Estes DataFrames e mapping devem ser carregados UMA VEZ no app.py e armazenados em app.config
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
                "currentModuleInfo": {},
                "courseSummaries": [],
                "recentActivities": []
            })

        # --- Determinação do Módulo Atual ---
        current_date = datetime.now()
        current_app.logger.debug(f"[{datetime.now()}] Data atual para determinação do módulo: {current_date.strftime('%Y-%m-%d %H:%M:%S')}")

        modules = [
            {"number": 1, "start": datetime(2025, 3, 3), "end": datetime(2025, 5, 4, 23, 59, 59, 999999), "display_name": "Módulo 1"},
            {"number": 2, "start": datetime(2025, 5, 5), "end": datetime(2025, 6, 24, 23, 59, 59, 999999), "display_name": "Módulo 2"}, # CORRIGIDO AQUI
            {"number": 3, "start": datetime(2025, 6, 25), "end": datetime(2025, 8, 25, 23, 59, 59, 999999), "display_name": "Módulo 3"}, # CORRIGIDO AQUI
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

        # Ajustar as datas de filtro para cobrir o dia inteiro (já feito na definição dos módulos acima)
        current_module_info_start_date = current_module_info["start_date"]
        current_module_info_end_date = current_module_info["end_date"]
        current_app.logger.info(f"[{datetime.now()}] Datas de filtro: Início={current_module_info_start_date}, Fim={current_module_info_end_date}")

        # --- Lógica de Filtro e Cálculo de Métricas (Mantida, pois você disse que funcionava) ---
        # Assegurar que 'time_dt' é datetime no cache de logs, que deveria vir assim do app.py
        # (Se não estiver, o problema é no carregamento em app.py)
        if not pd.api.types.is_datetime64_any_dtype(df_raw_logs_cache['time_dt']):
             current_app.logger.error(f"[{datetime.now()}] 'time_dt' em df_raw_logs_cache não é datetime. Isso indica um problema no carregamento em app.py.")
             return jsonify({"error": "Erro interno: Formato de data inválido nos logs brutos."}), 500
        
        filtered_logs_by_module = df_raw_logs_cache[
            (df_raw_logs_cache['time_dt'] >= current_module_info_start_date) &
            (df_raw_logs_cache['time_dt'] <= current_module_info_end_date)
        ]
        current_app.logger.info(f"[{datetime.now()}] Logs APÓS FILTRO DE PERÍODO DO MÓDULO ({current_module_info_start_date} a {current_module_info_end_date}): {len(filtered_logs_by_module)} linhas.")

        # Garantir que 'course_fullname' existe nos logs brutos
        if 'course_fullname' not in filtered_logs_by_module.columns:
            current_app.logger.error(f"[{datetime.now()}] Coluna 'course_fullname' ausente nos logs filtrados.")
            return jsonify({"error": "Erro interno: Coluna de curso ausente."}), 500

        filtered_logs_for_professor = filtered_logs_by_module[
            filtered_logs_by_module['course_fullname'].isin(professor_courses)
        ].copy() # Usar .copy() para evitar SettingWithCopyWarning
        current_app.logger.info(f"[{datetime.now()}] Logs APÓS FILTRO DE CURSO DO PROFESSOR: {len(filtered_logs_for_professor)} linhas. (Cursos: {professor_courses})")

        # --- Cálculos Principais ---
        total_students = filtered_logs_for_professor['user_id'].nunique()
        
        students_at_risk_df = df_risk_scores_cache[
            df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique()) &
            df_risk_scores_cache['is_at_risk'] == 1
        ]
        students_at_risk = students_at_risk_df['user_id'].nunique()
        current_app.logger.debug(f"[{datetime.now()}] Total de alunos para {professor_id}: {total_students}, Alunos em risco: {students_at_risk}")

        # Total de atividades (ainda calculando, mas a view não usa)
        total_activities = len(filtered_logs_for_professor)

        # --- Resumo por Curso ---
        course_summaries_list = []
        if not filtered_logs_for_professor.empty:
            students_in_course_raw = filtered_logs_for_professor.groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsInCourse')
            
            # Garante que df_risk_scores_cache e df_features_cache não são vazios antes de filtrar
            valid_risk_users = df_risk_scores_cache['user_id'].unique() if not df_risk_scores_cache.empty else []
            valid_feature_users = df_features_cache['user_id'].unique() if not df_features_cache.empty else []

            df_risk_scores_professor_courses = df_risk_scores_cache[
                (df_risk_scores_cache['course_fullname'].isin(professor_courses)) &
                (df_risk_scores_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique())) &
                (df_risk_scores_cache['user_id'].isin(valid_risk_users)) # Reforça a validação de user_id
            ].copy()
            
            students_at_risk_in_course = df_risk_scores_professor_courses[df_risk_scores_professor_courses['is_at_risk'] == 1] \
                                            .groupby('course_fullname')['user_id'].nunique().reset_index(name='StudentsAtRiskInCourse')
            
            df_features_professor_courses = df_features_cache[
                (df_features_cache['course_fullname'].isin(professor_courses)) &
                (df_features_cache['user_id'].isin(filtered_logs_for_professor['user_id'].unique())) &
                (df_features_cache['user_id'].isin(valid_feature_users)) # Reforça a validação de user_id
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
        # Removido da View, mas o modelo C# ainda o espera.
        recent_activities_data = []
        # CORREÇÃO AQUI: user_ids_in_module será uma lista (se filtered_logs_for_professor estiver vazio)
        user_ids_in_module = filtered_logs_for_professor['user_id'].unique().tolist() if not filtered_logs_for_professor.empty else []

        # CORREÇÃO AQUI: Usar len() para verificar se a lista não está vazia
        if not df_raw_logs_cache.empty and len(user_ids_in_module) > 0: # <-- Mudança aqui
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

                    # --- Construção do Nome da Atividade ---
                    if target_info:
                        nome_atividade = f"{action_info} {target_info}"
                    else:
                        nome_atividade = action_info
                    
                    # Para 'Status', como a coluna 'status' não existe, usamos N/A ou inferimos algo básico de 'action'
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

        # --- Prepara e Retorna a resposta JSON final ---
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
            "recentActivities": recent_activities_data
        }

        current_app.logger.debug(f"[{datetime.now()}] Dados de resposta final: {json.dumps(response_data, indent=2, default=str)}")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"[{datetime.now()}] Erro inesperado na função get_professor_dashboard_data: {e}", exc_info=True)
        return jsonify({"error": "Erro interno do servidor Flask", "details": str(e)}), 500


