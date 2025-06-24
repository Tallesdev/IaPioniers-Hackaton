import pandas as pd
import os

# Caminho para o seu arquivo .pkl
pkl_file_path = r'C:\Users\talle\source\repos\IaPioniers\IaPioniers\unifenas_api_python\local_data\raw_logs_cache.pkl'

# Caminho para onde o CSV será salvo
csv_output_path = r'C:\Users\talle\source\repos\IaPioniers\IaPioniers\unifenas_api_python\local_data\raw_logs_cache.csv'

try:
    # Carrega o DataFrame do arquivo .pkl
    df_raw_logs = pd.read_pickle(pkl_file_path)

    # Salva o DataFrame em um arquivo CSV
    # O index=False é importante para não adicionar uma coluna de índice ao CSV
    df_raw_logs.to_csv(csv_output_path, index=False)

    print(f"DataFrame salvo com sucesso em: {csv_output_path}")
    print("Primeiras 5 linhas do DataFrame:")
    print(df_raw_logs.head())
    print("\nColunas do DataFrame:")
    print(df_raw_logs.columns)

except FileNotFoundError:
    print(f"Erro: O arquivo .pkl não foi encontrado em {pkl_file_path}")
except Exception as e:
    print(f"Ocorreu um erro ao carregar ou salvar o arquivo: {e}")