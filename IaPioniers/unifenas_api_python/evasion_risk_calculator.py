# evasion_risk_calculator.py
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# Importa as utilidades de calendário acadêmico que são relevantes para thresholds de tempo
import academic_calendar_utils

# --- Constantes de Risco ---
# Scores base:
POINTS_GLOBAL_INACTIVITY = 15
POINTS_COURSE_INACTIVITY = 7
POINTS_LOW_INTERACTIONS_GLOBAL = 7
POINTS_LOW_INTERACTIONS_COURSE = 2
POINTS_NO_FORUM_ACTIVITY = 4
POINTS_NO_QUIZ_ACTIVITY = 2

# Novos scores e thresholds
POINTS_NO_FIRST_ACTIVITY_SUBMISSION = 15
POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE = 10
POINTS_NO_MAIN_EXAM_SUBMISSION = 25
POINTS_LOW_RESOURCE_ENGAGEMENT = 5
POINTS_SILENT_EVASION = 8

# Thresholds de inatividade (em dias acadêmicos)
INACTIVITY_THRESHOLD_GLOBAL_DAYS = 30
INACTIVITY_THRESHOLD_COURSE_DAYS = 14

# Definindo um threshold de risco padrão para 'is_at_risk'
DEFAULT_RISK_THRESHOLD = 10

# --- FUNÇÕES DE CÁLCULO DE RISCO ---

def calculate_evasion_risk_scores(df_processed_features: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o score de risco de evasão para cada aluno/curso com base nas features processadas.
    Retorna um DataFrame com 'user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk' e 'evasion_reasons'.
    """
    print(f"DEBUG ERC: [{datetime.now()}] Iniciando cálculo de risco de evasão. Total de linhas de features: {len(df_processed_features)}")
    print(f"DEBUG ERC: [{datetime.now()}] Colunas do df_processed_features recebido: {df_processed_features.columns.tolist()}")
    print(f"DEBUG ERC: [{datetime.now()}] Amostra de df_processed_features recebido:\n{df_processed_features.head().to_string()}")


    if df_processed_features.empty:
        print(f"DEBUG ERC: [{datetime.now()}] DataFrame de features está vazio, retornando DataFrame de risco vazio.")
        return pd.DataFrame(columns=['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons'])

    df_risks = df_processed_features.copy()

    df_risks['overall_evasion_score'] = 0
    df_risks['evasion_reasons'] = ""
    df_risks['is_at_risk'] = 0 

    for index, row in df_risks.iterrows():
        score = 0
        reasons_list = [] 
        user_id_debug = row.get('user_id', 'N/A')
        course_name_debug = row.get('course_fullname', 'N/A')
        print(f"\nDEBUG ERC: [{datetime.now()}] Processando aluno: {user_id_debug}, Curso: {course_name_debug}")

        # Regras de Risco (BASEADAS NAS FEATURES)
        # Usar .get() com valor padrão e verificar pd.notna para robustez
        
        # Inatividade Global
        days_since_last_access_global = row.get('days_since_last_access_global', -1) # Default -1 para não ativar
        if pd.notna(days_since_last_access_global) and days_since_last_access_global >= INACTIVITY_THRESHOLD_GLOBAL_DAYS:
            score += POINTS_GLOBAL_INACTIVITY
            reasons_list.append("Inatividade Global: Não acessa o Moodle globalmente há muito tempo.")
            print(f"DEBUG ERC:  - Regra ativada: Inatividade Global ({POINTS_GLOBAL_INACTIVITY} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Inatividade Global' NÃO ativada. days_since_last_access_global: {days_since_last_access_global}")


        # Inatividade em Curso
        days_since_last_access_course = row.get('days_since_last_access_course', -1) # Default -1
        if pd.notna(days_since_last_access_course) and days_since_last_access_course >= INACTIVITY_THRESHOLD_COURSE_DAYS:
            score += POINTS_COURSE_INACTIVITY
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Inatividade em Curso: Não acessa '{course_name}' há muito tempo.")
            print(f"DEBUG ERC:  - Regra ativada: Inatividade em Curso ({POINTS_COURSE_INACTIVITY} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Inatividade em Curso' NÃO ativada. days_since_last_access_course: {days_since_last_access_course}")


        # Baixas Interações Globais
        total_actions_global = row.get('total_actions_global', 0)
        # Esta regra agora depende apenas de total_actions_global, pois days_since_last_access_global é tratado acima
        if pd.notna(total_actions_global) and total_actions_global < 50: # Removida a dependência de days_since_last_access_global < INACTIVITY_THRESHOLD_GLOBAL_DAYS
            score += POINTS_LOW_INTERACTIONS_GLOBAL
            reasons_list.append("Baixas Interações Globais: Poucas ações totais no Moodle.")
            print(f"DEBUG ERC:  - Regra ativada: Baixas Interações Globais ({POINTS_LOW_INTERACTIONS_GLOBAL} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Baixas Interações Globais' NÃO ativada. total_actions_global: {total_actions_global}")


        # Baixas Interações em Curso
        course_total_actions = row.get('course_total_actions', 0)
        # Esta regra agora depende apenas de course_total_actions
        if pd.notna(course_total_actions) and course_total_actions < 10: # Removida a dependência de days_since_last_access_course < INACTIVITY_THRESHOLD_COURSE_DAYS
            score += POINTS_LOW_INTERACTIONS_COURSE
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Baixas Interações em Curso: Poucas ações em '{course_name}'.")
            print(f"DEBUG ERC:  - Regra ativada: Baixas Interações em Curso ({POINTS_LOW_INTERACTIONS_COURSE} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Baixas Interações em Curso' NÃO ativada. course_total_actions: {course_total_actions}")


        # Ausência de Atividade em Fóruns
        global_forum_posts_count = row.get('global_forum_posts_count', 0)
        if pd.notna(global_forum_posts_count) and global_forum_posts_count == 0:
            score += POINTS_NO_FORUM_ACTIVITY
            reasons_list.append("Ausência de Atividade em Fóruns: Nenhuma postagem global no Moodle.")
            print(f"DEBUG ERC:  - Regra ativada: Ausência de Atividade em Fóruns ({POINTS_NO_FORUM_ACTIVITY} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Ausência de Atividade em Fóruns' NÃO ativada. global_forum_posts_count: {global_forum_posts_count}")


        # Ausência de Atividade em Quizzes/Provas
        global_quiz_attempts_count = row.get('global_quiz_attempts_count', 0)
        if pd.notna(global_quiz_attempts_count) and global_quiz_attempts_count == 0:
            score += POINTS_NO_QUIZ_ACTIVITY
            reasons_list.append("Ausência de Atividade em Quizzes/Provas: Nenhuma tentativa global no Moodle.")
            print(f"DEBUG ERC:  - Regra ativada: Ausência de Atividade em Quizzes/Provas ({POINTS_NO_QUIZ_ACTIVITY} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Ausência de Atividade em Quizzes/Provas' NÃO ativada. global_quiz_attempts_count: {global_quiz_attempts_count}")


        # Ausência de Submissão na Primeira Atividade
        is_in_first_activity_cycle_no_submission = row.get('is_in_first_activity_cycle_no_submission', False)
        if pd.notna(is_in_first_activity_cycle_no_submission) and is_in_first_activity_cycle_no_submission:
            score += POINTS_NO_FIRST_ACTIVITY_SUBMISSION
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Ausência de Submissão na Primeira Atividade em '{course_name}'.")
            print(f"DEBUG ERC:  - Regra ativada: Ausência de Submissão na Primeira Atividade ({POINTS_NO_FIRST_ACTIVITY_SUBMISSION} pts). Score atual: {score}")
            
            # Alto Risco: Sem submissão e sem interação visual recente
            has_recent_visual_interaction_in_cycle = row.get('has_recent_visual_interaction_in_cycle', True) # Default True para não ativar a regra se a feature estiver faltando
            if pd.notna(has_recent_visual_interaction_in_cycle) and not has_recent_visual_interaction_in_cycle:
                score += POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE
                reasons_list.append(f"Alto Risco: Sem submissão e sem interação visual recente em '{course_name}'.")
                print(f"DEBUG ERC:  - Regra ativada: Alto Risco (Sem submissão/interação) ({POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE} pts). Score atual: {score}")
            else:
                print(f"DEBUG ERC:  - Regra 'Alto Risco (Sem submissão/interação)' NÃO ativada. has_recent_visual_interaction_in_cycle: {has_recent_visual_interaction_in_cycle}")
        else:
            print(f"DEBUG ERC:  - Regra 'Ausência de Submissão na Primeira Atividade' NÃO ativada. is_in_first_activity_cycle_no_submission: {is_in_first_activity_cycle_no_submission}")


        # Baixo Engajamento com Recursos
        unique_resource_types_accessed_course = row.get('unique_resource_types_accessed_course', 0)
        if pd.notna(unique_resource_types_accessed_course) and unique_resource_types_accessed_course < 3: 
            score += POINTS_LOW_RESOURCE_ENGAGEMENT
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Baixo Engajamento com Recursos: Poucos tipos de conteúdo acessados em '{course_name}'.")
            print(f"DEBUG ERC:  - Regra ativada: Baixo Engajamento com Recursos ({POINTS_LOW_RESOURCE_ENGAGEMENT} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Baixo Engajamento com Recursos' NÃO ativada. unique_resource_types_accessed_course: {unique_resource_types_accessed_course}")
            
        # Evasão Silenciosa
        has_falling_trend_90_days = row.get('has_falling_trend_90_days', False)
        if pd.notna(has_falling_trend_90_days) and has_falling_trend_90_days:
            score += POINTS_SILENT_EVASION
            reasons_list.append("Evasão Silenciosa: Tendência de queda na atividade global nos últimos 90 dias.")
            print(f"DEBUG ERC:  - Regra ativada: Evasão Silenciosa ({POINTS_SILENT_EVASION} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Evasão Silenciosa' NÃO ativada. has_falling_trend_90_days: {has_falling_trend_90_days}")


        # Ausência de Submissão na Prova Principal
        has_main_exam_submission = row.get('has_main_exam_submission', False) # Default False
        if pd.notna(has_main_exam_submission) and not has_main_exam_submission:
            score += POINTS_NO_MAIN_EXAM_SUBMISSION
            reasons_list.append("Ausência de Submissão na Prova Principal: Nenhuma submissão detectada para a prova principal.")
            print(f"DEBUG ERC:  - Regra ativada: Ausência de Submissão na Prova Principal ({POINTS_NO_MAIN_EXAM_SUBMISSION} pts). Score atual: {score}")
        else:
            print(f"DEBUG ERC:  - Regra 'Ausência de Submissão na Prova Principal' NÃO ativada. has_main_exam_submission: {has_main_exam_submission}")


        df_risks.at[index, 'overall_evasion_score'] = score
        df_risks.at[index, 'evasion_reasons'] = "; ".join(sorted(filter(None, set(reasons_list))))
        print(f"DEBUG ERC:  - Score final para {user_id_debug}/{course_name_debug}: {score}, Razões: {reasons_list}")


    df_risks['is_at_risk'] = (df_risks['overall_evasion_score'] >= DEFAULT_RISK_THRESHOLD).astype(int)

    df_risks.loc[df_risks['evasion_reasons'] == "", 'evasion_reasons'] = "Nenhuma razão detectada pelas regras."
    
    print(f"\nDEBUG ERC: [{datetime.now()}] Cálculo de risco de evasão concluído. Total de alunos em risco: {df_risks['is_at_risk'].sum()}")
    print(f"DEBUG ERC: [{datetime.now()}] DEFAULT_RISK_THRESHOLD: {DEFAULT_RISK_THRESHOLD}")
    print(f"DEBUG ERC: [{datetime.now()}] df_risks (primeiras 10 linhas com score e is_at_risk):\n{df_risks[['user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']].head(10).to_string()}")
    print(f"DEBUG ERC: [{datetime.now()}] Contagem final de is_at_risk:\n{df_risks['is_at_risk'].value_counts().to_string()}")

    return df_risks[['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']]
