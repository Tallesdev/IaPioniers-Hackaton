# moodle_data_processor.py
import pandas as pd
from datetime import datetime

# --- Funções de Processamento de Dados (MOVIDAS DO moodle_api_connector.py) ---

def process_raw_logs_dataframe(df_raw_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza o pós-processamento dos logs brutos do Moodle em um DataFrame.
    Assegura que colunas essenciais existem e estão no formato correto.
    """
    if df_raw_logs.empty:
        print(f"[{datetime.now()}] DataFrame de logs brutos está vazio, pulando o processamento de dados.")
        # Retorna um DataFrame com as colunas esperadas para evitar erros downstream
        expected_cols = [
            'date', 'user_id', 'user_name', 'course_id', 'course_fullname', 'course_category_name',
            'action', 'component', 'eventname'
        ]
        return pd.DataFrame(columns=expected_cols)

    df_logs = df_raw_logs.copy()

    print(f"[{datetime.now()}] Iniciando processamento do DataFrame de logs brutos. Linhas iniciais: {len(df_logs)}")

    # 1. Garante que 'date' é datetime e lida com erros de conversão
    df_logs['date'] = pd.to_datetime(df_logs['date'], errors='coerce')

    # 2. Garante que 'user_id' é string
    df_logs['user_id'] = df_logs['user_id'].astype(str)

    # 3. Trata valores ausentes ou inválidos em 'date' e 'user_id'
    # Remover linhas onde 'date' ou 'user_id' são nulos após conversão/coerção
    df_logs.dropna(subset=['date', 'user_id'], inplace=True)
    print(f"[{datetime.now()}] Linhas após dropar NaNs em 'date' e 'user_id': {len(df_logs)}")

    # 4. Garante que colunas essenciais existem e adiciona valores padrão se ausentes
    if 'user_name' not in df_logs.columns:
        if 'name' in df_logs.columns: # Tenta usar 'name' se 'user_name' não existir
            df_logs['user_name'] = df_logs['name']
        else:
            print(f"[{datetime.now()}] Aviso: Coluna 'user_name' ou 'name' não encontrada nos logs. Adicionando 'Usuário Desconhecido'.")
            df_logs['user_name'] = 'Usuário Desconhecido'

    if 'course_id' not in df_logs.columns:
        print(f"[{datetime.now()}] Aviso: Coluna 'course_id' não encontrada nos logs. Adicionando 'COURSE_UNKNOWN'.")
        df_logs['course_id'] = 'COURSE_UNKNOWN'

    if 'course_fullname' not in df_logs.columns:
        print(f"[{datetime.now()}] Aviso: Coluna 'course_fullname' não encontrada nos logs. Adicionando 'Curso Desconhecido'.")
        df_logs['course_fullname'] = 'Curso Desconhecido'

    if 'course_category_name' not in df_logs.columns:
        print(f"[{datetime.now()}] Aviso: Coluna 'course_category_name' não encontrada nos logs. Adicionando 'Categoria Desconhecida'.")
        df_logs['course_category_name'] = 'Categoria Desconhecida'
    
    # Colunas que podem ser relevantes para engenharia de features, mesmo que vazias
    if 'action' not in df_logs.columns:
        df_logs['action'] = 'unknown_action'
    if 'component' not in df_logs.columns:
        df_logs['component'] = 'unknown_component'
    if 'eventname' not in df_logs.columns:
        df_logs['eventname'] = 'unknown_event'

    # Opcional: Reordenar colunas para consistência
    cols_order = [
        'date', 'user_id', 'user_name', 'course_id', 'course_fullname', 'course_category_name',
        'action', 'component', 'eventname'
    ]
    # Adiciona colunas existentes que não estão na ordem, no final
    for col in df_logs.columns:
        if col not in cols_order:
            cols_order.append(col)
    
    df_logs = df_logs[cols_order]

    print(f"[{datetime.now()}] DataFrame processado. Total de linhas após ajuste de colunas: {len(df_logs)}")

    return df_logs