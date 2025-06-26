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
            print("DataFrame de logs brutos está vazio, retornando DataFrame de features vazio.")
            expected_cols = [
                'user_id', 'user_name', 'total_actions_global', 'days_since_last_access_global',
                'global_activity_last_30_days', 'global_activity_last_7_days',
                'total_courses_accessed_global', 'has_falling_trend_90_days',
                'course_id', 'course_fullname', 'course_category_name',
                'days_since_last_access_course', 'course_total_actions',
                'viewed_count_course', 'graded_count_course', 'days_since_last_valuable_submission_course',
                'is_in_first_activity_cycle_no_submission', 'has_recent_visual_interaction_in_cycle',
                'unique_resource_types_accessed_course',
                'total_submissions_course' # NOVA FEATURE ADICIONADA AQUI
            ]
            return pd.DataFrame(columns=expected_cols)

        df_logs = df_raw_logs.copy()

        df_logs['date'] = pd.to_datetime(df_logs['date'], errors='coerce')
        df_logs['user_id'] = df_logs['user_id'].astype(str)
        
        if 'action' in df_logs.columns:
            df_logs['action'] = df_logs['action'].astype(str)
        else:
            df_logs['action'] = 'unknown_action'
            
        if 'component' in df_logs.columns:
            df_logs['component'] = df_logs['component'].astype(str)
        else:
            df_logs['component'] = 'unknown_component'

        df_logs = df_logs.dropna(subset=['date', 'user_id'])

        current_date = datetime.now().date()

        print("Calculando features globais...")
        df_global_features = df_logs.groupby('user_id').agg(
            user_name=('user_name', 'first'),
            total_actions_global=('action', 'count'),
            last_access_date_global=('date', 'max'),
            total_courses_accessed_global=('course_id', 'nunique'),
            global_activity_last_30_days=('date', lambda x: x[x >= (datetime.now() - timedelta(days=30))].count()),
            global_activity_last_7_days=('date', lambda x: x[x >= (datetime.now() - timedelta(days=7))].count())
        ).reset_index()

        df_global_features['days_since_last_access_global'] = df_global_features['last_access_date_global'].apply(
            lambda x: calculate_academic_days_between(x.date(), current_date)
        )

        print("Calculando tendência de queda na atividade global...")
        date_90_days_ago = datetime.now() - timedelta(days=90)
        date_180_days_ago = datetime.now() - timedelta(days=180)

        df_recent_activity = df_logs[df_logs['date'] >= date_90_days_ago]
        df_previous_activity = df_logs[(df_logs['date'] >= date_180_days_ago) & (df_logs['date'] < date_90_days_ago)]

        recent_activity_counts = df_recent_activity.groupby('user_id')['action'].count().reindex(df_global_features['user_id']).fillna(0)
        previous_activity_counts = df_previous_activity.groupby('user_id')['action'].count().reindex(df_global_features['user_id']).fillna(0)

        df_global_features['has_falling_trend_90_days'] = ((recent_activity_counts < 0.5 * previous_activity_counts) & (previous_activity_counts > 0)).values

        print("Calculando features por curso...")
        df_course_features = df_logs.groupby(['user_id', 'course_id']).apply(lambda group: pd.Series({
            'user_name': group['user_name'].iloc[0],
            'course_fullname': group['course_fullname'].iloc[0],
            'course_category_name': group['course_category_name'].iloc[0],
            'last_access_date_course': group['date'].max(),
            'course_total_actions': group['action'].count(),
            'viewed_count_course': group['action'].str.contains('view', na=False).sum(),
            'graded_count_course': group['action'].str.contains('graded', na=False).sum(),
            'last_submission_date_course': group.loc[group['action'].str.contains('submit|submitted', na=False), 'date'].max(),
            'total_submissions_course': group['action'].str.contains('submit|submitted', na=False).sum(), # NOVA FEATURE
            'has_recent_visual_interaction_in_cycle': (
                (group['action'].str.contains('view', na=False) | group['action'].str.contains('access', na=False)) &
                (group['date'] >= (datetime.now() - timedelta(days=academic_calendar_utils.THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS)))
            ).any(),
            'unique_resource_types_accessed_course': group['component'].nunique()
        })).reset_index()


        df_course_features['days_since_last_access_course'] = df_course_features['last_access_date_course'].apply(
            lambda x: calculate_academic_days_between(x.date(), current_date)
        )

        df_course_features['days_since_last_valuable_submission_course'] = df_course_features['last_submission_date_course'].apply(
            lambda x: calculate_academic_days_between(x.date(), current_date) if pd.notna(x) else -1
        )

        df_course_features['is_in_first_activity_cycle_no_submission'] = df_course_features.apply(
            lambda row: academic_calendar_utils.is_in_first_activity_cycle_no_submission(
                current_date, row['last_submission_date_course'], datetime.now().date()
            ), axis=1
        )

        df_features = pd.merge(df_global_features, df_course_features, on=['user_id', 'user_name'], how='left')

        df_features.fillna({
            'course_id': 'UNKNOWN_COURSE',
            'course_fullname': 'Curso Desconhecido',
            'course_category_name': 'Categoria Desconhecida',
            'days_since_last_access_course': -1,
            'course_total_actions': 0,
            'viewed_count_course': 0,
            'graded_count_course': 0,
            'days_since_last_valuable_submission_course': -1,
            'is_in_first_activity_cycle_no_submission': False,
            'has_recent_visual_interaction_in_cycle': False,
            'unique_resource_types_accessed_course': 0,
            'total_submissions_course': 0 # Inicializar nova feature
        }, inplace=True)
        
        for col in ['days_since_last_access_course', 'course_total_actions', 'viewed_count_course', 
                    'graded_count_course', 'days_since_last_valuable_submission_course', 
                    'unique_resource_types_accessed_course', 'total_submissions_course']: # Incluir nova feature
            if col in df_features.columns:
                df_features[col] = df_features[col].astype(int)

        df_features.drop(columns=['last_access_date_global', 'last_access_date_course', 'last_submission_date_course'], errors='ignore', inplace=True)

        return df_features
    