import joblib
import pandas as pd
import os

# Ajuste este caminho para o seu arquivo raw_logs_cache.pkl
# Use o caminho completo para garantir que ele seja encontrado
path_to_raw_logs = 'C:\\Users\\talle\\source\\repos\\IaPioniers\\IaPioniers\\unifenas_api_python\\local_data\\raw_logs_cache.pkl'

print(f"Tentando carregar o arquivo: {path_to_raw_logs}")

try:
    df_raw_logs = joblib.load(path_to_raw_logs)
    print(f"Arquivo carregado com sucesso. Total de linhas: {len(df_raw_logs)}")

    print("\n--- Informações sobre as colunas de atividades e status ---")

    # Lista de colunas que podem conter informações relevantes
    potential_cols = ['action', 'eventname', 'target', 'object', 'status', 'name', 'description', 'grade_status', 'completion_status']

    for col in potential_cols:
        if col in df_raw_logs.columns:
            print(f"\nColuna '{col}':")
            print(f"  Tipo de dado: {df_raw_logs[col].dtype}")
            print(f"  Valores únicos (primeiros 10): {df_raw_logs[col].unique()[:10].tolist()}")
            print(f"  Contagem de valores nulos: {df_raw_logs[col].isnull().sum()} de {len(df_raw_logs)}")
        else:
            print(f"\nColuna '{col}' NÃO encontrada no DataFrame.")

    print("\n--- Exemplos de atividades (primeiras 20 linhas das colunas relevantes) ---")
    display_cols = [col for col in potential_cols if col in df_raw_logs.columns]
    if 'time_dt' in df_raw_logs.columns:
        display_cols.insert(0, 'time_dt')
    if 'user_name' in df_raw_logs.columns:
        display_cols.insert(1, 'user_name')
    elif 'user_id' in df_raw_logs.columns:
        display_cols.insert(1, 'user_id')

    print(df_raw_logs[display_cols].head(20).to_string())

except FileNotFoundError:
    print(f"ERRO: Arquivo '{path_to_raw_logs}' não encontrado. Verifique o caminho.")
except Exception as e:
    print(f"ERRO ao carregar ou processar o arquivo: {e}")