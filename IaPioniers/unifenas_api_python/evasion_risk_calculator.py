# evasion_risk_calculator.py
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# Importa as utilidades de calendário acadêmico que são relevantes para thresholds de tempo
import academic_calendar_utils # Certifique-se de que este módulo existe e é acessível

# --- Constantes de Risco ---
# Scores base:
POINTS_GLOBAL_INACTIVITY = 20
POINTS_COURSE_INACTIVITY = 15
POINTS_LOW_INTERACTIONS_GLOBAL = 10
POINTS_LOW_INTERACTIONS_COURSE = 8
POINTS_NO_FORUM_ACTIVITY = 5
POINTS_NO_QUIZ_ACTIVITY = 5

# Novos scores e thresholds
POINTS_NO_FIRST_ACTIVITY_SUBMISSION = 25
POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE = 40
POINTS_NO_MAIN_EXAM_SUBMISSION = 50 # Se a feature de submission existir
POINTS_LOW_RESOURCE_ENGAGEMENT = 10
POINTS_SILENT_EVASION = 20

# Thresholds de inatividade (em dias acadêmicos)
INACTIVITY_THRESHOLD_GLOBAL_DAYS = 30
INACTIVITY_THRESHOLD_COURSE_DAYS = 14

# Definindo um threshold de risco padrão para 'is_at_risk'
DEFAULT_RISK_THRESHOLD = 30

# --- FUNÇÕES DE CÁLCULO DE RISCO ---

def calculate_evasion_risk_scores(df_processed_features: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o score de risco de evasão para cada aluno/curso com base nas features processadas.
    Retorna um DataFrame com 'user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk' e 'evasion_reasons'.
    """
    print(f"[{datetime.now()}] Iniciando cálculo de risco de evasão. Total de linhas de features: {len(df_processed_features)}")

    if df_processed_features.empty:
        print(f"[{datetime.now()}] DataFrame de features está vazio, retornando DataFrame de risco vazio.")
        # É crucial retornar todas as colunas esperadas pelo merge em predict_evasion.py
        return pd.DataFrame(columns=['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons'])

    # Crie uma cópia do DataFrame de features. Isso mantém todas as features originais
    # e permite adicionar as novas colunas de risco.
    df_risks = df_processed_features.copy()

    # Inicializa colunas de risco
    df_risks['overall_evasion_score'] = 0
    df_risks['evasion_reasons'] = ""
    df_risks['is_at_risk'] = 0 # 0 = Não, 1 = Sim, será atualizado no final

    # Loop para aplicar as regras de risco
    for index, row in df_risks.iterrows():
        score = 0
        reasons_list = [] # Usar uma lista temporária para as razões de cada linha

        # Regras de Risco (BASEADAS NAS FEATURES)
        # 1. Inatividade Global (muito tempo sem acessar o Moodle)
        if 'days_since_last_access_global' in row and pd.notna(row['days_since_last_access_global']) and \
           row['days_since_last_access_global'] >= INACTIVITY_THRESHOLD_GLOBAL_DAYS:
            score += POINTS_GLOBAL_INACTIVITY
            reasons_list.append("Inatividade Global: Não acessa o Moodle globalmente há muito tempo.")

        # 2. Inatividade em Cursos Específicos
        if 'days_since_last_access_course' in row and pd.notna(row['days_since_last_access_course']) and \
           row['days_since_last_access_course'] >= INACTIVITY_THRESHOLD_COURSE_DAYS:
            score += POINTS_COURSE_INACTIVITY
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Inatividade em Curso: Não acessa '{course_name}' há muito tempo.")

        # 3. Baixas Interações Globais (poucas ações totais no Moodle)
        if 'total_actions_global' in row and pd.notna(row['total_actions_global']) and \
           'days_since_last_access_global' in row and pd.notna(row['days_since_last_access_global']):
            if row['total_actions_global'] < 50 and row['days_since_last_access_global'] < INACTIVITY_THRESHOLD_GLOBAL_DAYS:
                score += POINTS_LOW_INTERACTIONS_GLOBAL
                reasons_list.append("Baixas Interações Globais: Poucas ações totais no Moodle.")

        # 4. Baixas Interações em Cursos Específicos
        if 'course_total_actions' in row and pd.notna(row['course_total_actions']) and \
           'days_since_last_access_course' in row and pd.notna(row['days_since_last_access_course']):
            if row['course_total_actions'] < 10 and row['days_since_last_access_course'] < INACTIVITY_THRESHOLD_COURSE_DAYS:
                score += POINTS_LOW_INTERACTIONS_COURSE
                course_name = row.get('course_fullname', 'curso desconhecido')
                reasons_list.append(f"Baixas Interações em Curso: Poucas ações em '{course_name}'.")
        
        # 5. Ausência de Interação em Fóruns
        if 'global_forum_posts_count' in row and pd.notna(row['global_forum_posts_count']) and row['global_forum_posts_count'] == 0:
            score += POINTS_NO_FORUM_ACTIVITY
            reasons_list.append("Ausência de Atividade em Fóruns: Nenhuma postagem global no Moodle.")

        # 6. Ausência de Interação em Quizzes/Provas
        if 'global_quiz_attempts_count' in row and pd.notna(row['global_quiz_attempts_count']) and row['global_quiz_attempts_count'] == 0:
            score += POINTS_NO_QUIZ_ACTIVITY
            reasons_list.append("Ausência de Atividade em Quizzes/Provas: Nenhuma tentativa global no Moodle.")

        # 7. Ausência de Submissão na Primeira Atividade/Ciclo
        if 'is_in_first_activity_cycle_no_submission' in row and pd.notna(row['is_in_first_activity_cycle_no_submission']) and \
           row['is_in_first_activity_cycle_no_submission']:
            score += POINTS_NO_FIRST_ACTIVITY_SUBMISSION
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Ausência de Submissão na Primeira Atividade em '{course_name}'.")
            
            if 'has_recent_visual_interaction_in_cycle' in row and pd.notna(row['has_recent_visual_interaction_in_cycle']) and \
               not row['has_recent_visual_interaction_in_cycle']:
                score += POINTS_HIGH_RISK_NO_FIRST_ACTIVITY_OFFLINE
                reasons_list.append(f"Alto Risco: Sem submissão e sem interação visual recente em '{course_name}'.")

        # 8. Baixo Engajamento com Tipos de Recurso
        if 'unique_resource_types_accessed_course' in row and pd.notna(row['unique_resource_types_accessed_course']) and \
           row['unique_resource_types_accessed_course'] < 3:
            score += POINTS_LOW_RESOURCE_ENGAGEMENT
            course_name = row.get('course_fullname', 'curso desconhecido')
            reasons_list.append(f"Baixo Engajamento com Recursos: Poucos tipos de conteúdo acessados em '{course_name}'.")

        # 9. Evasão Silenciosa (tendência de queda na atividade global)
        if 'has_falling_trend_90_days' in row and pd.notna(row['has_falling_trend_90_days']) and \
           row['has_falling_trend_90_days']:
            score += POINTS_SILENT_EVASION
            reasons_list.append("Evasão Silenciosa: Tendência de queda na atividade global nos últimos 90 dias.")

        # --- Fim das Regras de Risco ---
        
        # Atribui o score e as razões APENAS UMA VEZ por iteração
        df_risks.at[index, 'overall_evasion_score'] = score
        df_risks.at[index, 'evasion_reasons'] = "; ".join(sorted(filter(None, set(reasons_list))))

        # O print de debug deve vir DEPOIS das atribuições finais para ver os valores corretos
        print(f"Aluno {row['user_name']} (Curso: {row['course_fullname']}): Score = {score}, Razões: {reasons_list}")


    # Determinar se o aluno está em risco com base no threshold
    df_risks['is_at_risk'] = (df_risks['overall_evasion_score'] >= DEFAULT_RISK_THRESHOLD).astype(int)

    # Preencher 'Nenhuma razão detectada pelas regras' para alunos sem razões
    df_risks.loc[df_risks['evasion_reasons'] == "", 'evasion_reasons'] = "Nenhuma razão detectada pelas regras."
    
    print(f"[{datetime.now()}] Cálculo de risco de evasão concluído. Total de alunos em risco: {df_risks['is_at_risk'].sum()}")
    
    # Retorna apenas as colunas essenciais para o uso no predict_evasion.py e no app.py
    return df_risks[['user_id', 'user_name', 'course_fullname', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons']]