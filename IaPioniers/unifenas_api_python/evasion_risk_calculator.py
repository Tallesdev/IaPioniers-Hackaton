# evasion_risk_calculator.py
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# Importa as utilidades de calendário acadêmico que são relevantes para thresholds de tempo
import academic_calendar_utils # Certifique-se de que este módulo existe e é acessível

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
DEFAULT_RISK_THRESHOLD = 5 # <--- Esta linha é a que me interessa!

# --- FUNÇÕES DE CÁLCULO DE RISCO ---

def calculate_evasion_risk_scores(df_processed_features: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o score de risco de evasão para cada aluno/curso com base nas features processadas.
    Retorna um DataFrame com 'user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk' e 'evasion_reasons'.
    """
    print(f"[{datetime.now()}] Iniciando cálculo de risco de evasão. Total de linhas de features: {len(df_processed_features)}")
    print(f"[{datetime.now()}] Colunas do df_processed_features recebido: {df_processed_features.columns.tolist()}")


    if df_processed_features.empty:
        print(f"[{datetime.now()}] DataFrame de features está vazio, retornando DataFrame de risco vazio.")
        return pd.DataFrame(columns=['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons'])

    df_risks = df_processed_features.copy()

    df_risks['overall_evasion_score'] = 0
    df_risks['evasion_reasons'] = ""
    df_risks['is_at_risk'] = 0 

    for index, row in df_risks.iterrows():
        score = 0
        reasons_list = [] 

        # Regras de Risco (BASEADAS NAS FEATURES)
        if 'days_since_last_access_global' in row and pd.notna(row['days_since_last_access_global']) and \
           row['days_since_last_access_global'] >= INACTIVITY_THRESHOLD_GLOBAL_DAYS:
            score += POINTS_GLOBAL_INACTIVITY
            reasons_list.append("Inatividade Global: Não acessa o Moodle globalmente há muito tempo.")

        if 'days_since_last_access_course' in row and pd.notna(row['days_since_last_access_course']) and \
           row['days_since_last_access_course'] >= INACTIVITY_THRESHOLD_COURSE_DAYS:
            score += POINTS_COURSE_INACTIVITY
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Inatividade em Curso: Não acessa '{course_name}' há muito tempo.")

        if 'total_actions_global' in row and pd.notna(row['total_actions_global']) and \
           'days_since_last_access_global' in row and pd.notna(row['days_since_last_access_global']):
            if row['total_actions_global'] < 50 and row['days_since_last_access_global'] < INACTIVITY_THRESHOLD_GLOBAL_DAYS:
                score += POINTS_LOW_INTERACTIONS_GLOBAL
                reasons_list.append("Baixas Interações Globais: Poucas ações totais no Moodle.")

        if 'course_total_actions' in row and pd.notna(row['course_total_actions']) and \
           'days_since_last_access_course' in row and pd.notna(row['days_since_last_access_course']):
            if row['course_total_actions'] < 10 and row['days_since_last_access_course'] < INACTIVITY_THRESHOLD_COURSE_DAYS:
                score += POINTS_LOW_INTERACTIONS_COURSE
                course_name = row.get('course_fullname', 'curso desconhecido')
                reasons_list.append(f"Baixas Interações em Curso: Poucas ações em '{course_name}'.")
        
        if 'global_forum_posts_count' in row and pd.notna(row['global_forum_posts_count']) and row['global_forum_posts_count'] == 0:
            score += POINTS_NO_FORUM_ACTIVITY
            reasons_list.append("Ausência de Atividade em Fóruns: Nenhuma postagem global no Moodle.")

        if 'global_quiz_attempts_count' in row and pd.notna(row['global_quiz_attempts_count']) and row['global_quiz_attempts_count'] == 0:
            score += POINTS_NO_QUIZ_ACTIVITY
            reasons_list.append("Ausência de Atividade em Quizzes/Provas: Nenhuma tentativa global no Moodle.")

        if 'is_in_first_activity_cycle_no_submission' in row and pd.notna(row['is_in_first_activity_cycle_no_submission']) and \
           row['is_in_first_activity_cycle_no_submission']:
            score += POINTS_NO_FIRST_ACTIVITY_SUBMISSION
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Ausência de Submissão na Primeira Atividade em '{course_name}'.")
            
            if 'has_recent_visual_interaction_in_cycle' in row and pd.notna(row['has_recent_visual_interaction_in_cycle']) and \
               not row['has_recent_visual_interaction_in_cycle']:
                score += POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE
                reasons_list.append(f"Alto Risco: Sem submissão e sem interação visual recente em '{course_name}'.")

        if 'unique_resource_types_accessed_course' in row and pd.notna(row['unique_resource_types_accessed_course']) and \
           row['unique_resource_types_accessed_course'] < 3: 
            score += POINTS_LOW_RESOURCE_ENGAGEMENT
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Baixo Engajamento com Recursos: Poucos tipos de conteúdo acessados em '{course_name}'.")
            
        if 'has_falling_trend_90_days' in row and pd.notna(row['has_falling_trend_90_days']) and \
           row['has_falling_trend_90_days']:
            score += POINTS_SILENT_EVASION
            reasons_list.append("Evasão Silenciosa: Tendência de queda na atividade global nos últimos 90 dias.")

        if 'has_main_exam_submission' in row and pd.notna(row['has_main_exam_submission']) and \
           not row['has_main_exam_submission']:
            score += POINTS_NO_MAIN_EXAM_SUBMISSION
            reasons_list.append("Ausência de Submissão na Prova Principal: Nenhuma submissão detectada para a prova principal.")

        df_risks.at[index, 'overall_evasion_score'] = score
        df_risks.at[index, 'evasion_reasons'] = "; ".join(sorted(filter(None, set(reasons_list))))

    df_risks['is_at_risk'] = (df_risks['overall_evasion_score'] >= DEFAULT_RISK_THRESHOLD).astype(int)

    df_risks.loc[df_risks['evasion_reasons'] == "", 'evasion_reasons'] = "Nenhuma razão detectada pelas regras."
    
    print(f"[{datetime.now()}] Cálculo de risco de evasão concluído. Total de alunos em risco: {df_risks['is_at_risk'].sum()}")
    print(f"[{datetime.now()}] DEFAULT_RISK_THRESHOLD: {DEFAULT_RISK_THRESHOLD}")
    print(f"[{datetime.now()}] df_risks (primeiras 10 linhas com score e is_at_risk):\n{df_risks[['user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']].head(10).to_string()}")
    print(f"[{datetime.now()}] Contagem final de is_at_risk:\n{df_risks['is_at_risk'].value_counts().to_string()}")

    return df_risks[['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']]
