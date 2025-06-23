# student_profile_generator.py

import pandas as pd
from datetime import datetime, timedelta

def get_student_profile_details(user_id: str, features_df: pd.DataFrame, risk_scores_df: pd.DataFrame, raw_logs_df: pd.DataFrame) -> dict:
    """
    Gera um perfil detalhado de um estudante, combinando features, scores de risco e logs recentes.
    Recebe os DataFrames de features, scores de risco e logs brutos como entrada.
    """
    student_profile = {
        "user_id": user_id,
        "user_name": None,
        "overall_evasion_score": 0.0, # Garantir que é float
        "is_at_risk": False,
        "evasion_reasons": [],
        "global_activity": {},
        "course_activity": [],
        "detailed_recent_logs": []
    }

    # 1. Obter informações de risco e nome do aluno
    user_risk_info = risk_scores_df[risk_scores_df['user_id'] == user_id]
    if not user_risk_info.empty:
        student_profile["user_name"] = str(user_risk_info['user_name'].iloc[0]) # Garantir string
        student_profile["overall_evasion_score"] = float(user_risk_info['overall_evasion_score'].iloc[0]) # Garantir float
        student_profile["is_at_risk"] = bool(user_risk_info['is_at_risk'].iloc[0]) # Garantir bool
        student_profile["evasion_reasons"] = list(user_risk_info['evasion_reasons'].iloc[0]) # Garantir lista
    else:
        user_feature_info = features_df[features_df['user_id'] == user_id]
        if not user_feature_info.empty:
            student_profile["user_name"] = str(user_feature_info['user_name'].iloc[0])
        return student_profile

    # 2. Obter features globais
    global_features = features_df[
        (features_df['user_id'] == user_id) & (features_df['course_id'] == 'UNKNOWN_COURSE')
    ]
    if not global_features.empty:
        gf = global_features.iloc[0]
        student_profile["global_activity"] = {
            "total_actions": int(gf.get('total_actions_global', 0)),
            "days_since_last_access": int(gf.get('days_since_last_access_global', -1)),
            "activity_last_30_days": int(gf.get('global_activity_last_30_days', 0)),
            "activity_last_7_days": int(gf.get('global_activity_last_7_days', 0)),
            "total_courses_accessed": int(gf.get('total_courses_accessed_global', 0)),
            "has_falling_trend_90_days": bool(gf.get('has_falling_trend_90_days', False)) # Garantir bool
        }

    # 3. Obter features por curso
    course_features = features_df[
        (features_df['user_id'] == user_id) & (features_df['course_id'] != 'UNKNOWN_COURSE')
    ].copy()
    
    if not course_features.empty:
        # Converter para lista de dicionários para JSON
        cols_to_drop = ['user_id', 'user_name'] 
        student_profile["course_activity"] = course_features.drop(columns=cols_to_drop, errors='ignore').to_dict(orient='records')
        
        # Iterar sobre cada dicionário de curso e garantir tipos nativos
        for course_dict in student_profile["course_activity"]:
            for key, value in course_dict.items():
                if pd.isna(value): # Tratar valores NaN
                    course_dict[key] = None
                elif isinstance(value, (pd.Int64Dtype, pd.Float64Dtype)): # Tipos específicos de Pandas
                    course_dict[key] = int(value) if pd.api.types.is_integer_dtype(value) else float(value)
                elif pd.api.types.is_integer_dtype(value): # Booleans também podem ser tratados como int 0/1
                    course_dict[key] = int(value)
                elif pd.api.types.is_float_dtype(value):
                    course_dict[key] = float(value)
                elif pd.api.types.is_bool_dtype(value):
                    course_dict[key] = bool(value) # Converter bool do numpy para bool python
                elif isinstance(value, datetime):
                    course_dict[key] = value.isoformat() # Convert datetime objects to string
                # Se for um tipo NumPy, converter para o tipo nativo Python
                elif hasattr(value, 'item') and callable(getattr(value, 'item')):
                    try:
                        course_dict[key] = value.item()
                    except TypeError:
                        pass # Fallback if .item() doesn't work for some reason


    # 4. Obter logs recentes (ex: últimos 30 dias)
    recent_logs = raw_logs_df[
        (raw_logs_df['user_id'] == user_id) &
        (raw_logs_df['date'] >= datetime.now() - timedelta(days=30))
    ]
    if not recent_logs.empty:
        student_profile["detailed_recent_logs"] = recent_logs[[
            'date', 'action', 'course_id', 'course_fullname'
        ]].sort_values(by='date', ascending=False).to_dict(orient='records')
        
        for log in student_profile["detailed_recent_logs"]:
            if isinstance(log['date'], datetime):
                log['date'] = log['date'].isoformat()


    return student_profile