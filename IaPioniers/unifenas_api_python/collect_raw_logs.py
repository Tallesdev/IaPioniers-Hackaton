# collect_raw_logs.py

import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Definição do caminho do cache dos logs brutos
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'local_data')
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')

# --- Seções de Configuração da API Moodle ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

REQUEST_DELAY_SECONDS = 0.5
MAX_CONCURRENT_REQUESTS = 5

RETRY_SETTINGS = {
    'stop': stop_after_attempt(5),
    'wait': wait_exponential(multiplier=1, min=2, max=60),
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': True
}

# --- Funções Assíncronas para a API Moodle (MANTENHA ESTAS AQUI) ---

@retry(**RETRY_SETTINGS)
async def get_access_token_async(email, password, api_base_url):
    """Obtém um token de acesso da API do Moodle de forma assíncrona."""
    url = f"{api_base_url}/get-token"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {"email": email, "password": password}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            response.raise_for_status()
            token_data = await response.json()
            return token_data.get("access_token")

@retry(**RETRY_SETTINGS)
async def get_moodle_users_async(token, api_base_url):
    """Lista os usuários do Moodle que acessaram recentemente de forma assíncrona."""
    url = f"{api_base_url}/moodle/usuarios"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

async def get_user_logs_async(session, user_id, token, api_base_url, semaphore, start_date: str = None, end_date: str = None):
    """
    Coleta os logs de acesso de um usuário específico de forma assíncrona com controle de concorrência,
    e agora suporta filtragem por período.
    start_date e end_date devem ser strings no formato 'YYYY-MM-DD'.
    """
    async with semaphore:
        await asyncio.sleep(REQUEST_DELAY_SECONDS)

        url = f"{api_base_url}/moodle/logs-usuario"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload = {"user_id": user_id}
        
        # Adicionar parâmetros de data se fornecidos
        if start_date:
            payload['start_date'] = start_date
        if end_date:
            payload['end_date'] = end_date

        try:
            @retry(**RETRY_SETTINGS)
            async def _fetch_single_log_with_retry():
                async with session.get(url, headers=headers, params=payload) as response:
                    response.raise_for_status()
                    return await response.json()
            
            return await _fetch_single_log_with_retry()

        except aiohttp.ClientError as e:
            print(f"[{datetime.now()}] Erro assíncrono final (após retries) ao obter logs para o usuário {user_id} no período {start_date} a {end_date}: {e}")
            return []

async def collect_all_moodle_logs_and_update_cache(email, password, api_base_url):
    """
    Coleta todos os logs de usuários do Moodle para um período definido (ou todos)
    e os anexa ao cache de logs brutos existente.
    """
    print(f"[{datetime.now()}] Iniciando coleta e atualização do cache de logs brutos...")

    # Carregar logs existentes do cache (se houver)
    df_existing_logs = pd.DataFrame()
    if os.path.exists(RAW_LOGS_CACHE_FILE):
        try:
            df_existing_logs = pd.read_pickle(RAW_LOGS_CACHE_FILE)
            print(f"[{datetime.now()}] {len(df_existing_logs)} logs existentes carregados do cache.")
            df_existing_logs['date'] = pd.to_datetime(df_existing_logs['date'], errors='coerce')
            df_existing_logs.dropna(subset=['date'], inplace=True)
            
            # Determinar a data mais recente nos logs existentes para coletar APENAS DADOS NOVOS
            # Adicione 1 segundo para garantir que não haja sobreposição com o último log.
            latest_date_in_cache = df_existing_logs['date'].max() if not df_existing_logs.empty else None
            if latest_date_in_cache:
                start_date_for_new_collection = (latest_date_in_cache + timedelta(seconds=1)).strftime('%Y-%m-%d')
                print(f"[{datetime.now()}] Coletando logs a partir de: {start_date_for_new_collection}")
            else:
                start_date_for_new_collection = "2024-01-01" # Ou alguma data inicial razoável para a primeira coleta
                print(f"[{datetime.now()}] Cache vazio ou inválido. Coletando logs desde: {start_date_for_new_collection}")

        except Exception as e:
            print(f"[{datetime.now()}] Erro ao carregar cache existente: {e}. Iniciando coleta do zero.")
            df_existing_logs = pd.DataFrame()
            start_date_for_new_collection = "2024-01-01" # Recomeça de uma data inicial se o cache estiver corrompido ou vazio

    else:
        print(f"[{datetime.now()}] Cache '{RAW_LOGS_CACHE_FILE}' não encontrado. Iniciando coleta do zero.")
        start_date_for_new_collection = "2024-01-01" # Defina uma data inicial razoável (ex: início do ano letivo)

    end_date_for_new_collection = datetime.now().strftime('%Y-%m-%d') # Coleta até a data atual

    async with aiohttp.ClientSession() as session:
        token = await get_access_token_async(email, password, api_base_url)
        if not token:
            print(f"[{datetime.now()}] Erro: Não foi possível obter o token de acesso. Abortando coleta de logs.")
            return

        print(f"[{datetime.now()}] Token obtido. Coletando lista de usuários...")
        users_data = await get_moodle_users_async(token, api_base_url)
        if not users_data:
            print(f"[{datetime.now()}] Erro: Não foi possível obter a lista de usuários. Abortando coleta de logs.")
            return

        print(f"[{datetime.now()}] {len(users_data)} usuários encontrados. Coletando logs individuais para o período {start_date_for_new_collection} a {end_date_for_new_collection}...")
        
        new_logs = []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        tasks = []
        for user in users_data:
            user_id = user.get('user_id')
            if user_id:
                tasks.append(get_user_logs_async(session, user_id, token, api_base_url, semaphore, 
                                                start_date=start_date_for_new_collection, 
                                                end_date=end_date_for_new_collection))
            else:
                print(f"[{datetime.now()}] Aviso: user_id não encontrado para o usuário: {user.get('name', 'N/A')}")

        if tasks:
            print(f"[{datetime.now()}] Executando {len(tasks)} tarefas de coleta de logs concorrentemente...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"[{datetime.now()}] Todas as tarefas de coleta de logs concluídas.")
        else:
            results = []
            print(f"[{datetime.now()}] Nenhuma tarefa de coleta de logs para executar.")

        for i, res in enumerate(results):
            user_info = users_data[i] # Assumimos que a ordem é mantida para correspondência
            user_id = user_info.get('user_id')
            user_name = user_info.get('name')

            if isinstance(res, Exception):
                print(f"[{datetime.now()}] Erro no processamento do log para o usuário {user_id}: {res}")
            elif res:
                for log in res:
                    log_entry = {
                        'user_id': user_id,
                        'user_name': user_name,
                        'user_lastaccess': user_info.get('user_lastaccess'),
                        'date': log.get('date'),
                        'eventname': log.get('eventname', ''), # Garante que 'eventname' existe
                        'action': log.get('action', ''),       # Garante que 'action' existe
                        'course_fullname': log.get('course_fullname', 'Curso Desconhecido'),
                        # Adicione outras chaves que você espera da API com valores padrão se necessário
                    }
                    new_logs.append(log_entry)
    
    df_new_logs = pd.DataFrame(new_logs)
    print(f"[{datetime.now()}] DataFrame de novos logs coletados. Total de linhas: {len(df_new_logs)}")

    if not df_new_logs.empty:
        df_new_logs['date'] = pd.to_datetime(df_new_logs['date'], errors='coerce')
        if pd.api.types.is_string_dtype(df_new_logs['user_lastaccess']):
            df_new_logs['user_lastaccess'] = pd.to_datetime(df_new_logs['user_lastaccess'], errors='coerce')
        elif pd.api.types.is_numeric_dtype(df_new_logs['user_lastaccess']):
            df_new_logs['user_lastaccess'] = pd.to_datetime(df_new_logs['user_lastaccess'], unit='s', errors='coerce')
        
        df_new_logs = df_new_logs.dropna(subset=['date'])
        
        # Assegura que 'course_fullname' existe, movido para dentro do loop para ser mais robusto
        # if 'course_fullname' not in df_new_logs.columns:
        #     df_new_logs['course_fullname'] = 'Curso Desconhecido'

        # Combinar logs existentes com novos logs
        if not df_existing_logs.empty:
            # Reindexa as colunas de df_existing_logs para garantir que 'eventname' e 'action' existam
            # antes da concatenação, se eles forem adicionados dinamicamente no df_new_logs
            # Isso é importante caso o cache antigo não tivesse essas colunas.
            missing_cols_in_existing = [col for col in ['eventname', 'action', 'course_fullname'] if col not in df_existing_logs.columns]
            for col in missing_cols_in_existing:
                df_existing_logs[col] = '' # Adiciona colunas ausentes com valor padrão

            df_combined_logs = pd.concat([df_existing_logs, df_new_logs], ignore_index=True)
            # Remover duplicatas com base em um conjunto de colunas que identificam um log único
            # Cuidado com 'date' se a granularidade não for exata (pode haver milissegundos diferentes)
            # Pode ser melhor usar um hash ou uma combinação de ID de usuário, curso, evento e timestamp (truncado)
            print(f"[{datetime.now()}] Total antes de remover duplicatas: {len(df_combined_logs)}")
            df_combined_logs.drop_duplicates(subset=['user_id', 'date', 'eventname', 'action'], inplace=True)
            print(f"[{datetime.now()}] Total após remover duplicatas: {len(df_combined_logs)}")
        else:
            df_combined_logs = df_new_logs.copy()
            print(f"[{datetime.now()}] Não havia logs existentes, novos logs serão o cache inicial.")

        # Salvar o DataFrame combinado de volta no cache
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        df_combined_logs.to_pickle(RAW_LOGS_CACHE_FILE)
        print(f"[{datetime.now()}] Cache de logs brutos atualizado e salvo em '{RAW_LOGS_CACHE_FILE}'. Total de linhas no cache: {len(df_combined_logs)}")
    else:
        print(f"[{datetime.now()}] Nenhuns novos logs coletados. Cache não foi atualizado.")


if __name__ == '__main__':
    asyncio.run(collect_all_moodle_logs_and_update_cache(
        UNIFENAS_EMAIL, UNIFENAS_PASSWORD, MOODLE_API_BASE_URL
    ))
