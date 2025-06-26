# feature_engineering.py
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter
import os

import academic_calendar_utils
from academic_calendar_utils import is_academic_recess, calculate_academic_days_between

def run_feature_engineering(df_raw_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza a engenharia de features a partir dos logs brutos do Moodle.
    Retorna um DataFrame com as features calculadas para cada usuário/curso.
    """
    if df_raw_logs.empty:
        print(f"DEBUG FE: [{datetime.now()}] DataFrame de logs brutos está vazio, retornando DataFrame de features vazio.")
        # Definir todas as colunas esperadas para um DataFrame vazio
        expected_cols = [
            'user_id', 'user_name', 'course_id', 'course_fullname', 'course_category_name',
            'total_actions_global', 'days_since_last_access_global',
            'global_activity_last_30_days', 'global_activity_last_7_days',
            'total_courses_accessed_global', 'has_falling_trend_90_days',
            'course_total_actions', 'viewed_count_course', 'graded_count_course',
            'days_since_last_access_course', 'days_since_last_valuable_submission_course',
            'is_in_first_activity_cycle_no_submission', 'has_recent_visual_interaction_in_cycle',
            'unique_resource_types_accessed_course', 'total_submissions_course',
            'global_forum_posts_count', 'global_quiz_attempts_count',
            'has_main_exam_submission' # Adicionando esta feature
        ]
        return pd.DataFrame(columns=expected_cols)

    df_logs = df_raw_logs.copy()

    # Garantir que 'date' é datetime e lidar com 'user_lastaccess'
    df_logs['date'] = pd.to_datetime(df_logs['date'], errors='coerce')
    if 'user_lastaccess' in df_logs.columns:
        if pd.api.types.is_numeric_dtype(df_logs['user_lastaccess']):
            df_logs['user_lastaccess'] = pd.to_datetime(df_logs['user_lastaccess'], unit='s', errors='coerce')
        else:
            df_logs['user_lastaccess'] = pd.to_datetime(df_logs['user_lastaccess'], errors='coerce')
    else:
        df_logs['user_lastaccess'] = df_logs['date'] # Fallback se não houver user_lastaccess

    # Garantir colunas essenciais como string e minúsculas para ações/componentes
    df_logs['user_id'] = df_logs['user_id'].astype(str)
    df_logs['user_name'] = df_logs['user_name'].astype(str)
    df_logs['course_id'] = df_logs['course_id'].astype(str) # Garante que course_id é string
    df_logs['course_fullname'] = df_logs['course_fullname'].astype(str)
    df_logs['course_category_name'] = df_logs['course_category_name'].astype(str)
    df_logs['action'] = df_logs['action'].astype(str).str.lower()
    df_logs['component'] = df_logs['component'].astype(str).str.lower()
    df_logs['target'] = df_logs['target'].astype(str).str.lower()


    # Remover linhas com datas inválidas
    df_logs.dropna(subset=['date', 'user_id', 'user_lastaccess'], inplace=True)
    if df_logs.empty:
        print(f"DEBUG FE: [{datetime.now()}] DataFrame vazio após remoção de datas inválidas.")
        return run_feature_engineering(pd.DataFrame()) # Retorna um DataFrame vazio com colunas esperadas

    current_date = datetime.now().date()
    current_datetime = datetime.now()

    print(f"DEBUG FE: [{datetime.now()}] Calculando features globais...")
    df_global_features = df_logs.groupby('user_id').agg(
        user_name=('user_name', 'first'),
        total_actions_global=('action', 'count'),
        last_access_date_global=('user_lastaccess', 'max'), # Usar user_lastaccess para global
        total_courses_accessed_global=('course_id', 'nunique'),
        global_activity_last_30_days=('date', lambda x: x[x >= (current_datetime - timedelta(days=30))].count()),
        global_activity_last_7_days=('date', lambda x: x[x >= (current_datetime - timedelta(days=7))].count()),
        global_forum_posts_count=('action', lambda x: x[x.str.contains('forum|discussion') | x.str.contains('posted|replied|created')].count()),
        global_quiz_attempts_count=('action', lambda x: x[x.str.contains('quiz') & x.str.contains('attempt|started|submitted')].count())
    ).reset_index()

    df_global_features['days_since_last_access_global'] = df_global_features['last_access_date_global'].apply(
        lambda x: calculate_academic_days_between(x.date(), current_date) if pd.notna(x) else -1
    )

    print(f"DEBUG FE: [{datetime.now()}] Calculando tendência de queda na atividade global...")
    date_90_days_ago = current_datetime - timedelta(days=90)
    date_180_days_ago = current_datetime - timedelta(days=180)

    df_recent_activity = df_logs[df_logs['date'] >= date_90_days_ago]
    df_previous_activity = df_logs[(df_logs['date'] >= date_180_days_ago) & (df_logs['date'] < date_90_days_ago)]

    recent_activity_counts = df_recent_activity.groupby('user_id')['action'].count().reindex(df_global_features['user_id']).fillna(0)
    previous_activity_counts = df_previous_activity.groupby('user_id')['action'].count().reindex(df_global_features['user_id']).fillna(0)

    # Evita divisão por zero: se não houve atividade anterior, não há tendência de queda
    df_global_features['has_falling_trend_90_days'] = ((recent_activity_counts < 0.5 * previous_activity_counts) & (previous_activity_counts > 0)).values
    print(f"DEBUG FE: [{datetime.now()}] has_falling_trend_90_days (amostra):\n{df_global_features[['user_id', 'has_falling_trend_90_days']].head()}")


    print(f"DEBUG FE: [{datetime.now()}] Calculando features por curso...")
    df_course_features = df_logs.groupby(['user_id', 'course_id']).apply(lambda group: pd.Series({
        'user_name': group['user_name'].iloc[0],
        'course_fullname': group['course_fullname'].iloc[0],
        'course_category_name': group['course_category_name'].iloc[0],
        'last_activity_date_course': group['date'].max(),
        'first_activity_date_in_course': group['date'].min(),
        'course_total_actions': group['action'].count(),
        'viewed_count_course': group['action'].str.contains('view', na=False).sum(),
        'graded_count_course': group['action'].str.contains('graded', na=False).sum(),
        'last_submission_date_course': group.loc[group['action'].str.contains('submit|submitted', na=False), 'date'].max(),
        'total_submissions_course': group['action'].str.contains('submit|submitted', na=False).sum(),
        'unique_resource_types_accessed_course': group['component'].nunique(),
        'has_main_exam_submission': (group['action'].str.contains('submitted', na=False) & group['target'].str.contains('prova principal', na=False)).any() # Nova feature
    })).reset_index()


    df_course_features['days_since_last_access_course'] = df_course_features['last_activity_date_course'].apply(
        lambda x: calculate_academic_days_between(x.date(), current_date) if pd.notna(x) else -1
    )

    df_course_features['days_since_last_valuable_submission_course'] = df_course_features['last_submission_date_course'].apply(
        lambda x: calculate_academic_days_between(x.date(), current_date) if pd.notna(x) else -1
    )

    FIRST_ACTIVITY_CYCLE_DAYS = 30 # Exemplo: Considera os primeiros 30 dias de atividade do aluno no curso
    df_course_features['is_in_first_activity_cycle_no_submission'] = df_course_features.apply(
        lambda row: (
            row['total_submissions_course'] == 0 and # Nenhuma submissão
            pd.notna(row['first_activity_date_in_course']) and # Tem uma data de primeira atividade
            (current_date - row['first_activity_date_in_course'].date()).days <= FIRST_ACTIVITY_CYCLE_DAYS # E está dentro do ciclo inicial
        ), axis=1
    )
    
    df_course_features['has_recent_visual_interaction_in_cycle'] = df_course_features.apply(
        lambda row: academic_calendar_utils.has_recent_visual_interaction_in_cycle(
            row['last_activity_date_course'].date() if pd.notna(row['last_activity_date_course']) else None,
            current_date
        ), axis=1
    )

    print(f"DEBUG FE: [{datetime.now()}] is_in_first_activity_cycle_no_submission (amostra):\n{df_course_features[['user_id', 'course_fullname', 'is_in_first_activity_cycle_no_submission']].head()}")
    print(f"DEBUG FE: [{datetime.now()}] has_recent_visual_interaction_in_cycle (amostra):\n{df_course_features[['user_id', 'course_fullname', 'has_recent_visual_interaction_in_cycle']].head()}")
    print(f"DEBUG FE: [{datetime.now()}] has_main_exam_submission (amostra):\n{df_course_features[['user_id', 'course_fullname', 'has_main_exam_submission']].head()}")


    # --- MERGE DE TODAS AS FEATURES EM UM ÚNICO DATAFRAME ---
    # Começa com as features globais e faz merge com as features de curso
    df_features = pd.merge(df_global_features, df_course_features, on=['user_id', 'user_name'], how='left', suffixes=('_global', '_course'))

    # Renomear colunas para consistência com o calculador de risco
    df_features.rename(columns={
        'course_total_actions_course': 'course_total_actions', # Remove o sufixo duplicado
        'viewed_count_course_course': 'viewed_count_course',
        'graded_count_course_course': 'graded_count_course',
        'total_submissions_course_course': 'total_submissions_course',
        'unique_resource_types_accessed_course_course': 'unique_resource_types_accessed_course'
    }, inplace=True)


    # Lidar com NaNs que possam surgir de merges (alunos sem atividades em certos cursos)
    # Preencher NaNs em colunas numéricas com 0 ou -1 (para dias desde acesso/submissão)
    # Adicionando todas as colunas que podem ser NaN e que são usadas nas regras
    df_features.fillna({
        'course_id': 'UNKNOWN_COURSE',
        'course_fullname': 'Curso Desconhecido',
        'course_category_name': 'Categoria Desconhecida',
        'days_since_last_access_global': -1,
        'global_activity_last_30_days': 0,
        'global_activity_last_7_days': 0,
        'total_courses_accessed_global': 0,
        'total_actions_global': 0,
        'global_forum_posts_count': 0,
        'global_quiz_attempts_count': 0,
        'days_since_last_access_course': -1,
        'course_total_actions': 0,
        'viewed_count_course': 0,
        'graded_count_course': 0,
        'days_since_last_valuable_submission_course': -1,
        'unique_resource_types_accessed_course': 0,
        'total_submissions_course': 0,
    }, inplace=True)
    
    # Preencher NaNs em colunas booleanas com False
    boolean_cols_to_fill = [
        'has_falling_trend_90_days',
        'is_in_first_activity_cycle_no_submission',
        'has_recent_visual_interaction_in_cycle',
        'has_main_exam_submission'
    ]
    for col in boolean_cols_to_fill:
        if col in df_features.columns:
            df_features[col] = df_features[col].fillna(False)
        else:
            df_features[col] = False # Adiciona a coluna se ela não existir e preenche com False

    # Converter colunas numéricas para int onde apropriado
    int_cols = [
        'days_since_last_access_global', 'global_activity_last_30_days', 'global_activity_last_7_days',
        'total_courses_accessed_global', 'total_actions_global', 'global_forum_posts_count', 'global_quiz_attempts_count',
        'days_since_last_access_course', 'course_total_actions', 'viewed_count_course', 'graded_count_course',
        'days_since_last_valuable_submission_course', 'unique_resource_types_accessed_course', 'total_submissions_course'
    ]
    for col in int_cols:
        if col in df_features.columns:
            df_features[col] = df_features[col].astype(int)

    # Remover colunas temporárias de data/hora que não são features finais
    df_features.drop(columns=[col for col in ['last_access_date_global', 'last_activity_date_course', 'last_submission_date_course', 'first_activity_date_in_course'] if col in df_features.columns], errors='ignore', inplace=True)

    # Criar a variável alvo: is_evaded (para treinamento do modelo de ML)
    # Um aluno é considerado "evadido" se o seu 'days_since_last_access_global' ou 'days_since_last_access_course'
    # exceder o limiar de inatividade.
    INACTIVITY_THRESHOLD_DAYS_FOR_EVASION = 30 # Definir um threshold para a variável alvo
    df_features['is_evaded'] = ((df_features['days_since_last_access_global'] >= INACTIVITY_THRESHOLD_DAYS_FOR_EVASION) |
                                 (df_features['days_since_last_access_course'] >= INACTIVITY_THRESHOLD_DAYS_FOR_EVASION)).astype(int)


    print(f"DEBUG FE: [{datetime.now()}] Features finais geradas (amostra):\n{df_features.head().to_string()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'is_in_first_activity_cycle_no_submission':\n{df_features['is_in_first_activity_cycle_no_submission'].value_counts()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'has_recent_visual_interaction_in_cycle':\n{df_features['has_recent_visual_interaction_in_cycle'].value_counts()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'has_falling_trend_90_days':\n{df_features['has_falling_trend_90_days'].value_counts()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'has_main_exam_submission':\n{df_features['has_main_exam_submission'].value_counts()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'days_since_last_access_global':\n{df_features['days_since_last_access_global'].value_counts()}")
    print(f"DEBUG FE: [{datetime.now()}] Contagem de valores para 'days_since_last_access_course':\n{df_features['days_since_last_access_course'].value_counts()}")

    return df_features
