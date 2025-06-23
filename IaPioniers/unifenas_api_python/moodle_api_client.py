# moodle_api_client.py
import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from tenacity import retry # Apenas retry é necessário aqui, as configurações vêm do config

# Importa as configurações da API
from moodle_api_config import MOODLE_API_BASE_URL, UNIFENAS_EMAIL, UNIFENAS_PASSWORD, \
    REQUEST_DELAY_SECONDS, MAX_CONCURRENT_REQUESTS, RETRY_SETTINGS

# Importa process_raw_logs_dataframe aqui para evitar circular dependency
from moodle_data_processor import process_raw_logs_dataframe

# --- Funções Assíncronas para a API Moodle ---

@retry(**RETRY_SETTINGS)
async def get_access_token_async(email, password, api_base_url):
    # ... (esta função permanece a mesma) ...
    url = f"{api_base_url}/get-token"
    payload = json.dumps({"email": email, "password": password})
    headers = {'Content-Type': 'application/json'}
    
    print(f"[{datetime.now()}] Tentando obter token de acesso...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=payload) as response:
            response.raise_for_status()
            data = await response.json()
            token = data.get("access_token")
            if not token:
                raise ValueError("Token de acesso não encontrado na resposta da API.")
            print(f"[{datetime.now()}] Token de acesso obtido com sucesso.")
            return token

@retry(**RETRY_SETTINGS)
async def get_moodle_users_async(token: str, api_base_url: str) -> list:
    # ... (esta função permanece a mesma) ...
    url = f"{api_base_url}/moodle/usuarios"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    print(f"[{datetime.now()}] Tentando coletar lista de usuários do Moodle em {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            users_data = await response.json()
            print(f"[{datetime.now()}] Lista de usuários coletada com sucesso. Total de usuários: {len(users_data)}")
            return users_data

# Esta função é a que estava gerando o warning indiretamente.
# Ela é decorada com retry, o que já a torna robusta.
@retry(**RETRY_SETTINGS)
async def get_moodle_user_logs_async(token: str, api_base_url: str, user_id: str) -> list:
    url = f"{api_base_url}/moodle/logs-usuario"
    params = {'user_id': user_id}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    # AQUI, O 'async with aiohttp.ClientSession()' DEVE SER PASSADO PARA A FUNÇÃO PRINCIPAL
    # OU CRIADO AQUI, MAS PARA REAPROVEITAMENTO, É MELHOR PASSÁ-LO.
    # No entanto, a retry decorator já cuida disso se a função é self-contained.
    # Vamos manter a criação de sessão aqui, pois o retry funciona bem com ela.
    print(f"[{datetime.now()}] Tentando coletar logs para o usuário {user_id} em {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            logs_data = await response.json()
            print(f"[{datetime.now()}] Logs para o usuário {user_id} coletados com sucesso. Total de entradas: {len(logs_data)}")
            return logs_data

async def collect_all_moodle_logs_async(email: str, password: str, api_base_url: str) -> pd.DataFrame:
    """
    Orquestra a coleta de todos os logs do Moodle em dois passos:
    1. Obtém a lista de usuários.
    2. Para cada usuário, busca seus logs específicos.
    3. Combina todos os logs em um único DataFrame.
    """
    all_combined_logs = []
    
    try:
        # 1. Obter token de acesso
        token = await get_access_token_async(email, password, api_base_url)

        # 2. Obter lista de usuários
        users = await get_moodle_users_async(token, api_base_url)
        
        # Extrair user_ids
        user_ids = [user.get('user_id') for user in users if user.get('user_id')]
        
        if not user_ids:
            print(f"[{datetime.now()}] Nenhuns user_ids encontrados, retornando DataFrame vazio.")
            return pd.DataFrame()

        # 3. Coletar logs para cada usuário de forma concorrente
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def fetch_user_logs_with_semaphore(user_id):
            async with semaphore:
                # Adicionar um pequeno delay para ser mais amigável à API
                await asyncio.sleep(REQUEST_DELAY_SECONDS) 
                # A função get_moodle_user_logs_async JÁ É UMA COROUTINE.
                # Precisamos chamá-la para OBTER a coroutine e então aguardá-la.
                return await get_moodle_user_logs_async(token, api_base_url, user_id)

        # Cria a lista de corrotinas (chamadas para fetch_user_logs_with_semaphore)
        tasks = [fetch_user_logs_with_semaphore(user_id) for user_id in user_ids]
        
        # Executa todas as corrotinas concorrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"[{datetime.now()}] Erro ao coletar logs para um usuário: {result}")
            else:
                all_combined_logs.extend(result)
            
        if not all_combined_logs:
            print(f"[{datetime.now()}] Nenhuns logs combinados de usuários, retornando DataFrame vazio.")
            return pd.DataFrame()

        df_raw_logs = pd.DataFrame(all_combined_logs)
        df_raw_logs = process_raw_logs_dataframe(df_raw_logs) # Processa o DataFrame combinado
        
        print(f"[{datetime.now()}] Logs coletados em DataFrame. Total de linhas: {len(df_raw_logs)}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Erro fatal na coleta de logs do Moodle: {e}")
        df_raw_logs = pd.DataFrame()

    return df_raw_logs

# A função `collect_all_moodle_logs` para compatibilidade (chamada pelo update_cache.py)
async def collect_all_moodle_logs(email, password, api_base_url):
    return await collect_all_moodle_logs_async(email, password, api_base_url)

if __name__ == '__main__':
    async def main_test_client():
        print("Testando moodle_api_client.py com coleta de logs de usuários específicos...")
        try:
            df_logs = await collect_all_moodle_logs_async(UNIFENAS_EMAIL, UNIFENAS_PASSWORD, MOODLE_API_BASE_URL)
            print(f"Logs coletados (amostra):\n{df_logs.head()}")
            print(f"Total de logs coletados: {len(df_logs)}")
            print(f"User IDs únicos nos logs: {df_logs['user_id'].nunique()}")

        except Exception as e:
            print(f"Erro durante o teste: {e}")

    asyncio.run(main_test_client())