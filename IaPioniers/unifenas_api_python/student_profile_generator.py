# student_profile_generator.py

import pandas as pd
from datetime import datetime, timedelta
import json # Importar para tratar strings JSON se 'evasion_reasons' vier como tal
import numpy as np # Adicionado para tipos numéricos do numpy

def get_student_profile_details(user_id: str, features_df: pd.DataFrame, risk_scores_df: pd.DataFrame, raw_logs_df: pd.DataFrame) -> dict:
    """
    Gera um perfil detalhado de um estudante, combinando features, scores de risco e logs recentes.
    Recebe os DataFrames de features, scores de risco e logs brutos como entrada.
    """
    print(f"DEBUG: [{datetime.now()}] Iniciando get_student_profile_details para user_id: {user_id}")

    student_profile = {
        "user_id": user_id,
        "user_name": f"Aluno {user_id}", # Default user name
        "overall_evasion_score": 0.0,
        "is_at_risk": False,
        "evasion_reasons": [],
        "global_activity": {},
        "course_activity": [],
        "detailed_recent_logs": []
    }

    # 1. Obter informações de risco e nome do aluno
    # Filtra por user_id e garante que a coluna 'user_name' existe no risk_scores_df
    user_risk_info = risk_scores_df[(risk_scores_df['user_id'] == user_id)].copy()
    
    if not user_risk_info.empty:
        print(f"DEBUG: [{datetime.now()}] Encontrado user_risk_info para {user_id}.")
        # Use .get() para acessar colunas com segurança, ou verifique a existência
        student_profile["user_name"] = str(user_risk_info['user_name'].iloc[0]) if 'user_name' in user_risk_info.columns and pd.notna(user_risk_info['user_name'].iloc[0]) else f"Aluno {user_id}"
        student_profile["overall_evasion_score"] = float(user_risk_info['overall_evasion_score'].iloc[0]) if 'overall_evasion_score' in user_risk_info.columns and pd.notna(user_risk_info['overall_evasion_score'].iloc[0]) else 0.0
        student_profile["is_at_risk"] = bool(user_risk_info['is_at_risk'].iloc[0]) if 'is_at_risk' in user_risk_info.columns and pd.notna(user_risk_info['is_at_risk'].iloc[0]) else False
        
        # Tratamento mais robusto para 'evasion_reasons'
        if 'evasion_reasons' in user_risk_info.columns and pd.notna(user_risk_info['evasion_reasons'].iloc[0]):
            reasons = user_risk_info['evasion_reasons'].iloc[0]
            if isinstance(reasons, str):
                try:
                    # Tenta carregar como JSON (se for string de lista, ex: "['motivo']")
                    parsed_reasons = json.loads(reasons.replace("'", "\"")) # Substitui aspas simples por duplas para json.loads
                    if isinstance(parsed_reasons, list):
                        student_profile["evasion_reasons"] = parsed_reasons
                    else:
                        student_profile["evasion_reasons"] = [str(reasons)] # Se não é lista, trata como string única
                except (json.JSONDecodeError, ValueError):
                    student_profile["evasion_reasons"] = [str(reasons)] # Se falhar, trata como string única
            elif isinstance(reasons, list):
                student_profile["evasion_reasons"] = reasons
            else:
                student_profile["evasion_reasons"] = [str(reasons)] # Fallback
        else:
            student_profile["evasion_reasons"] = [] # Default para vazio
    else:
        # Se não houver info de risco, tenta pegar o nome do features_df
        print(f"DEBUG: [{datetime.now()}] user_risk_info vazio para {user_id}. Tentando features_df para nome.")
        user_feature_info = features_df[features_df['user_id'] == user_id]
        if not user_feature_info.empty and 'user_name' in user_feature_info.columns and pd.notna(user_feature_info['user_name'].iloc[0]):
            student_profile["user_name"] = str(user_feature_info['user_name'].iloc[0])
        print(f"DEBUG: [{datetime.now()}] Retornando perfil básico para {user_id}, sem dados de risco completos.")
        # Retorna o perfil básico se não houver dados de risco para o user_id
        return student_profile 

    # 2. Obter features globais
    # CORREÇÃO AQUI: Não filtra mais por 'UNKNOWN_COURSE'. Pega as features globais da primeira linha do usuário.
    user_features_global_candidate = features_df[features_df['user_id'] == user_id].iloc[0] if not features_df[features_df['user_id'] == user_id].empty else None

    if user_features_global_candidate is not None:
        print(f"DEBUG: [{datetime.now()}] Encontrado features globais para {user_id}.")
        gf = user_features_global_candidate
        student_profile["global_activity"] = {
            "total_actions": int(gf.get('total_actions_global', 0)),
            "days_since_last_access": int(gf.get('overall_last_access_days_ago', -1)), # Usar overall_last_access_days_ago
            "activity_last_30_days": int(gf.get('global_activity_last_30_days', 0)), # Esta feature pode precisar ser gerada
            "activity_last_7_days": int(gf.get('global_activity_last_7_days', 0)),  # Esta feature pode precisar ser gerada
            "total_courses_accessed": int(gf.get('total_courses_accessed_global', 0)),
            "has_falling_trend_90_days": bool(gf.get('has_falling_trend_90_days', False))
        }
    else:
        print(f"DEBUG: [{datetime.now()}] Nenhuma feature global encontrada para {user_id}. Initializing empty.")
        student_profile["global_activity"] = {
            "total_actions": 0, "days_since_last_access": -1,
            "activity_last_30_days": 0, "activity_last_7_days": 0,
            "total_courses_accessed": 0, "has_falling_trend_90_days": False
        }


    # 3. Obter features por curso
    # Mudando 'course_id' para 'course_fullname' (já feito nas versões anteriores)
    course_features = features_df[
        (features_df['user_id'] == user_id) & (features_df['course_fullname'] != 'UNKNOWN_COURSE')
    ].copy()
    
    if not course_features.empty:
        print(f"DEBUG: [{datetime.now()}] Encontrado course_features para {user_id}.")
        # Usar uma lista de colunas esperadas para evitar erros se colunas estiverem faltando
        expected_course_cols = [
            'course_fullname', 'course_activity_count', 'course_unique_actions',
            'course_last_activity_days_ago', 'course_activity_duration_days',
            'engagement_per_day', 'unique_resource_types_accessed_course'
        ]
        
        # Filtra apenas as colunas que realmente existem no DataFrame e são esperadas
        available_course_cols = [col for col in expected_course_cols if col in course_features.columns]
        
        student_profile["course_activity"] = course_features[available_course_cols].to_dict(orient='records')
        
        # Iterar sobre cada dicionário de curso e garantir tipos nativos
        for course_dict in student_profile["course_activity"]:
            for key, value in course_dict.items():
                if pd.isna(value):
                    course_dict[key] = None
                elif isinstance(value, (pd.Int64Dtype, pd.Float64Dtype, np.int64, np.float64)):
                    if pd.api.types.is_integer_dtype(value):
                        course_dict[key] = int(value)
                    elif pd.api.types.is_float_dtype(value):
                        course_dict[key] = float(value)
                elif pd.api.types.is_bool_dtype(value):
                    course_dict[key] = bool(value)
                elif isinstance(value, datetime):
                    course_dict[key] = value.isoformat()
                # Adiciona uma verificação para objetos de data/hora do Pandas
                elif pd.api.types.is_datetime64_any_dtype(value):
                    course_dict[key] = value.isoformat()
                # Tenta converter outros tipos NumPy para Python nativo
                elif hasattr(value, 'item') and callable(getattr(value, 'item')):
                    try:
                        course_dict[key] = value.item()
                    except (TypeError, ValueError):
                        pass # Fallback if .item() doesn't work for some reason
    else:
        print(f"DEBUG: [{datetime.now()}] Nenhuma course_features encontrada para {user_id}. Initializing empty.")

    # 4. Obter logs recentes (ex: últimos 30 dias)
    # CORREÇÃO AQUI: Usar a coluna 'time_dt' que deve ser criada no app.py para os logs brutos
    if 'time_dt' in raw_logs_df.columns and pd.api.types.is_datetime64_any_dtype(raw_logs_df['time_dt']):
        print(f"DEBUG: [{datetime.now()}] Coluna 'time_dt' encontrada e é datetime.")
        recent_logs = raw_logs_df[
            (raw_logs_df['user_id'] == user_id) &
            (raw_logs_df['time_dt'] >= datetime.now() - timedelta(days=30))
        ].copy() # Usar .copy() para evitar SettingWithCopyWarning
        
        if not recent_logs.empty:
            print(f"DEBUG: [{datetime.now()}] Encontrado {len(recent_logs)} logs recentes para {user_id}.")
            expected_log_cols = ['time_dt', 'action', 'course_fullname', 'target', 'component'] # Usar 'time_dt'
            available_log_cols = [col for col in expected_log_cols if col in recent_logs.columns]
            
            student_profile["detailed_recent_logs"] = recent_logs[available_log_cols].sort_values(by='time_dt', ascending=False).to_dict(orient='records')
            
            for log in student_profile["detailed_recent_logs"]:
                if 'time_dt' in log and pd.api.types.is_datetime64_any_dtype(log['time_dt']):
                    log['time_dt'] = log['time_dt'].isoformat()
                # Renomear 'time_dt' para 'date' na saída JSON para consistência externa, se desejar
                log['date'] = log.pop('time_dt') # Move e renomeia
        else:
            print(f"DEBUG: [{datetime.now()}] Nenhum log recente encontrado para {user_id} nos últimos 30 dias.")
    else:
        print(f"DEBUG: [{datetime.now()}] Coluna 'time_dt' não encontrada ou não é datetime no raw_logs_df. Não é possível processar logs recentes.")
        # Se 'date' for a única opção, podemos tentar um fallback, mas 'time_dt' é preferível
        if 'date' in raw_logs_df.columns and pd.api.types.is_datetime64_any_dtype(raw_logs_df['date']):
            print(f"DEBUG: [{datetime.now()}] Usando 'date' como fallback para logs recentes.")
            recent_logs = raw_logs_df[
                (raw_logs_df['user_id'] == user_id) &
                (raw_logs_df['date'] >= datetime.now() - timedelta(days=30))
            ].copy()
            if not recent_logs.empty:
                expected_log_cols = ['date', 'action', 'course_fullname', 'target', 'component']
                available_log_cols = [col for col in expected_log_cols if col in recent_logs.columns]
                student_profile["detailed_recent_logs"] = recent_logs[available_log_cols].sort_values(by='date', ascending=False).to_dict(orient='records')
                for log in student_profile["detailed_recent_logs"]:
                    if 'date' in log and pd.api.types.is_datetime64_any_dtype(log['date']):
                        log['date'] = log['date'].isoformat()
        else:
            print(f"DEBUG: [{datetime.now()}] raw_logs_df vazio ou inválido para processamento de logs recentes. Ou colunas 'time_dt'/'date' não adequadas.")

    print(f"DEBUG: [{datetime.now()}] Finalizando get_student_profile_details para user_id: {user_id}")
    return student_profile
