# predict_evasion.py
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import joblib

# Importar as funções de processamento de features do process_evasion_data.py
from process_evasion_data import process_moodle_logs_for_evasion

# Importar a função de cálculo de risco do evasion_risk_calculator.py
from evasion_risk_calculator import calculate_evasion_risk_scores

# Definir diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# Criar diretórios se não existirem
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


# Definição do caminho do cache e do modelo (para carregamento)
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')
MODEL_FILENAME = 'evasion_model.joblib'
FEATURES_FILENAME = 'model_features.json'
MODEL_PATH = os.path.join(LOCAL_DATA_DIR, MODEL_FILENAME)
FEATURES_PATH = os.path.join(LOCAL_DATA_DIR, FEATURES_FILENAME)

# Caminho para o arquivo de scores de risco que o app.py espera, salvo no CACHE_DIR
APP_RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')

# Definição do caminho do cache para features (adicione este)
APP_FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv')


# --- Seções de Configuração para Coleta de Logs (mantidas mas não usadas nesta versão do predict_evasion) ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

REQUEST_DELAY_SECONDS = 1.7
MAX_CONCURRENT_REQUESTS = 5

RETRY_SETTINGS = {
    'stop': stop_after_attempt(10),
    'wait': wait_exponential(multiplier=1, min=5, max=180),
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': False
}

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
        
        if start_date:
            payload['start_date'] = start_date
        if end_date:
            payload['end_date'] = end_date

        try:            
            async with session.get(url, headers=headers, params=payload) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro HTTP {e.status} para o usuário {user_id} no período {start_date} a {end_date}: {e.message}")
            return []
        except aiohttp.ClientError as e:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro de conexão ou outro erro de cliente para o usuário {user_id} no período {start_date} a {end_date}: {e}")
            return []

async def collect_recent_moodle_logs_for_prediction(email, password, api_base_url, days_to_look_back: int = 30):
    """
    Coleta logs recentes da API para fins de previsão.
    """
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando coleta de logs recentes para previsão (últimos {days_to_look_back} dias)...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_look_back)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    async with aiohttp.ClientSession() as session:
        token = await get_access_token_async(email, password, api_base_url)
        if not token:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Não foi possível obter o token de acesso. Abortando coleta de logs para previsão.")
            return pd.DataFrame()

        users_data = await get_moodle_users_async(token, api_base_url)
        if not users_data:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Não foi possível obter a lista de usuários para previsão.")
            return pd.DataFrame()

        recent_logs = []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        tasks = []
        for user in users_data:
            user_id = user.get('user_id')
            user_name = user.get('name')
            if user_id:
                tasks.append(get_user_logs_async(session, user_id, token, api_base_url, semaphore, start_date_str, end_date_str))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            user_info = users_data[i]
            user_id = user_info.get('user_id')
            user_name = user_info.get('name')
            
            if isinstance(res, Exception):
                print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao coletar logs recentes para o usuário {user_id}: {res}")
            elif res:
                for log in res:
                    log['user_id'] = user_id
                    log['user_name'] = user_name
                    log['user_lastaccess'] = user_info.get('user_lastaccess')
                    recent_logs.append(log)
    
    df_recent_logs = pd.DataFrame(recent_logs)
    print(f"DEBUG PREDICT: [{datetime.now()}] Total de logs recentes coletados para previsão: {len(df_recent_logs)}")
    
    if not df_recent_logs.empty:
        df_recent_logs['date'] = pd.to_datetime(df_recent_logs['date'], errors='coerce')
        if pd.api.types.is_string_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], errors='coerce')
        elif pd.api.types.is_numeric_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], unit='s', errors='coerce')
            
        df_recent_logs = df_recent_logs.dropna(subset=['date'])
        if 'course_fullname' not in df_recent_logs.columns:
            df_recent_logs['course_fullname'] = 'Curso Desconhecido'
        if 'eventname' not in df_recent_logs.columns:
            df_recent_logs['eventname'] = 'Evento Desconhecido'
        if 'action' not in df_recent_logs.columns:
            df_recent_logs['action'] = 'Ação Desconhecida'

    return df_recent_logs


async def run_evasion_prediction():
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando o processo de previsão de evasão...")

    # 1. Carregar o modelo e a lista de features (ainda do LOCAL_DATA_DIR)
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURES_PATH):
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Arquivos do modelo ('{MODEL_FILENAME}') ou de features ('{FEATURES_FILENAME}') não encontrados em '{LOCAL_DATA_DIR}'.")
        print(f"DEBUG PREDICT: [{datetime.now()}] Certifique-se de ter executado 'process_evasion_data.py' para treinar e salvar o modelo.")
        return

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, 'r') as f:
        model_features = json.load(f)
    print(f"DEBUG PREDICT: [{datetime.now()}] Modelo e lista de features carregados. Features esperadas: {model_features}")

    # --- MODIFICAÇÃO AQUI: CARREGAR LOGS DO CACHE EM VEZ DE COLETAR NOVAMENTE ---
    print(f"DEBUG PREDICT: [{datetime.now()}] Carregando logs brutos do cache para previsão: {RAW_LOGS_CACHE_FILE}...")
    if not os.path.exists(RAW_LOGS_CACHE_FILE):
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Arquivo de cache de logs brutos '{RAW_LOGS_CACHE_FILE}' não encontrado.")
        print(f"DEBUG PREDICT: [{datetime.now()}] Por favor, execute 'collect_raw_logs.py' (ou a função de coleta de logs da API) para gerar este arquivo.")
        return pd.DataFrame() # Retorna um DataFrame vazio se o cache não existir

    try:
        df_raw_logs_for_prediction = pd.read_pickle(RAW_LOGS_CACHE_FILE)
        print(f"DEBUG PREDICT: [{datetime.now()}] Logs brutos carregados do cache. Total de logs: {len(df_raw_logs_for_prediction)}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao carregar logs brutos do cache '{RAW_LOGS_CACHE_FILE}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro de carregamento

    if df_raw_logs_for_prediction.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum log disponível no cache para previsão. Abortando.")
        return

    print("DEBUG PREDICT: Logs brutos carregados (amostra):")
    print(df_raw_logs_for_prediction.head())
    
    # 3. Processar os dados brutos para extrair as mesmas features
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando processamento de features para evasão...")
    df_features_for_prediction = process_moodle_logs_for_evasion(df_raw_logs_for_prediction, inactivity_threshold_days=30)
    print(f"DEBUG PREDICT: [{datetime.now()}] Processamento de features concluído.")

    print(f"DEBUG PREDICT: [{datetime.now()}] Total de entradas de features (alunos x cursos): {len(df_features_for_prediction)}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Amostra de features geradas:\n{df_features_for_prediction.head()}")
    
    # Debug prints para as features, conforme solicitado anteriormente
    print(f"DEBUG PREDICT: [{datetime.now()}] Colunas em df_features_for_prediction: {df_features_for_prediction.columns.tolist()}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Amostra de df_features_for_prediction antes do calculador de risco:")
    print(df_features_for_prediction.head().to_string())
    if 'days_since_last_access_global' in df_features_for_prediction.columns:
        print(f"DEBUG PREDICT: [{datetime.now()}] Média e Máx de days_since_last_access_global: {df_features_for_prediction['days_since_last_access_global'].mean()} / {df_features_for_prediction['days_since_last_access_global'].max()}")
    if 'is_in_first_activity_cycle_no_submission' in df_features_for_prediction.columns:
        print(f"DEBUG PREDICT: [{datetime.now()}] Contagem de is_in_first_activity_cycle_no_submission True: {df_features_for_prediction['is_in_first_activity_cycle_no_submission'].sum()}")
    
    if df_features_for_prediction.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum feature processada para previsão. DataFrame de features vazio.")
        return

    # SALVAR df_features_for_prediction AQUI para o app.py consumir
    try:
        df_features_for_prediction.to_csv(APP_FEATURES_FILE, index=False, encoding='utf-8')
        print(f"DEBUG PREDICT: [{datetime.now()}] Features processadas salvas para o app.py em: {APP_FEATURES_FILE}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao salvar features processadas: {e}")
    
    # Preparar as features para a previsão do modelo de ML
    # Certifique-se de que todas as colunas esperadas pelo modelo estão presentes, preenchendo com 0 se ausentes
    for feature in model_features:
        if feature not in df_features_for_prediction.columns:
            df_features_for_prediction[feature] = 0
    X_predict = df_features_for_prediction[model_features].fillna(0)


    # 4. Realizar a Previsão do Modelo de ML
    print(f"DEBUG PREDICT: [{datetime.now()}] Realizando previsões para {len(X_predict)} entradas com o modelo de ML...")
    predictions = model.predict(X_predict)
    prediction_probabilities = model.predict_proba(X_predict)[:, 1]
    
    # Adicionar as previsões ao DataFrame de features
    df_features_for_prediction['predicted_evaded_ml'] = predictions
    df_features_for_prediction['evasion_probability_ml'] = prediction_probabilities

    # 5. Calcular o score de risco baseado em regras usando evasion_risk_calculator
    print(f"DEBUG PREDICT: [{datetime.now()}] Calculando scores de risco baseados em regras...")

    # LISTA COMPLETA DE COLUNAS QUE evasion_risk_calculator.py ESPERA
    cols_for_rule_based = [
        'user_id', 'user_name', 'course_id', 'course_fullname', 'course_category_name',
        'days_since_last_access_global',
        'days_since_last_access_course',
        'total_actions_global',
        'course_total_actions',
        'global_forum_posts_count',
        'global_quiz_attempts_count',
        'is_in_first_activity_cycle_no_submission',
        'has_recent_visual_interaction_in_cycle',
        'unique_resource_types_accessed_course',
        'has_falling_trend_90_days',
        'has_main_exam_submission' # Esta feature deve ser gerada em feature_engineering.py
    ]
    
    # Garante que apenas as colunas necessárias e existentes sejam selecionadas
    # E adiciona as colunas ausentes com valores padrão (False para booleanos, 0 para numéricos)
    df_for_rule_based = df_features_for_prediction.copy()
    for col in cols_for_rule_based:
        if col not in df_for_rule_based.columns:
            if col in ['is_in_first_activity_cycle_no_submission', 'has_recent_visual_interaction_in_cycle', 
                        'has_falling_trend_90_days', 'has_main_exam_submission']:
                df_for_rule_based[col] = False
            elif col in ['days_since_last_access_global', 'days_since_last_access_course',
                          'total_actions_global', 'course_total_actions', 'global_forum_posts_count',
                          'global_quiz_attempts_count', 'unique_resource_types_accessed_course']:
                df_for_rule_based[col] = 0
            else:
                df_for_rule_based[col] = None # Para outras colunas não mapeadas

    df_for_rule_based = df_for_rule_based[cols_for_rule_based] # Seleciona as colunas na ordem correta

    print(f"DEBUG PREDICT: [{datetime.now()}] DataFrame passado para calculate_evasion_risk_scores (amostra):\n{df_for_rule_based.head().to_string()}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Colunas do DataFrame passado para calculate_evasion_risk_scores: {df_for_rule_based.columns.tolist()}")


    df_rule_based_risks = calculate_evasion_risk_scores(df_for_rule_based)

    if df_rule_based_risks.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum score de risco baseado em regras gerado. Abortando salvamento de risk_scores_cache.")
        return

    # 6. Combinar os resultados:
    df_final_risk_scores = pd.merge(
        df_rule_based_risks,
        df_features_for_prediction[['user_id', 'course_fullname', 'predicted_evaded_ml', 'evasion_probability_ml']],
        on=['user_id', 'course_fullname'],
        how='left'
    )
    
    final_columns = [
        'user_id',
        'user_name',
        'course_fullname',
        'overall_evasion_score',
        'is_at_risk',
        'evasion_reasons',
        'predicted_evaded_ml',
        'evasion_probability_ml'
    ]
    
    df_risk_scores_to_save = df_final_risk_scores[final_columns]

    # 7. Salvar o DataFrame de scores de risco completo para o CACHE_DIR com o nome esperado pelo app.py
    try:
        df_risk_scores_to_save.to_csv(APP_RISK_SCORES_FILE, index=False, encoding='utf-8')
        print(f"DEBUG PREDICT: [{datetime.now()}] Scores de risco detalhados salvos para o app.py em: {APP_RISK_SCORES_FILE}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao salvar '{APP_RISK_SCORES_FILE}': {e}")


    print(f"DEBUG PREDICT: [{datetime.now()}] Processo de previsão de evasão concluído.")

# Bloco de execução principal para predict_evasion.py
if __name__ == '__main__':
    asyncio.run(run_evasion_prediction())
# predict_evasion.py
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import joblib

# Importar as funções de processamento de features do process_evasion_data.py
from process_evasion_data import process_moodle_logs_for_evasion

# Importar a função de cálculo de risco do evasion_risk_calculator.py
from evasion_risk_calculator import calculate_evasion_risk_scores

# Definir diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# Criar diretórios se não existirem
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


# Definição do caminho do cache e do modelo (para carregamento)
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')
MODEL_FILENAME = 'evasion_model.joblib'
FEATURES_FILENAME = 'model_features.json'
MODEL_PATH = os.path.join(LOCAL_DATA_DIR, MODEL_FILENAME)
FEATURES_PATH = os.path.join(LOCAL_DATA_DIR, FEATURES_FILENAME)

# Caminho para o arquivo de scores de risco que o app.py espera, salvo no CACHE_DIR
APP_RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')

# Definição do caminho do cache para features (adicione este)
APP_FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv')


# --- Seções de Configuração para Coleta de Logs (mantidas mas não usadas nesta versão do predict_evasion) ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

REQUEST_DELAY_SECONDS = 1.7
MAX_CONCURRENT_REQUESTS = 5

RETRY_SETTINGS = {
    'stop': stop_after_attempt(10),
    'wait': wait_exponential(multiplier=1, min=5, max=180),
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': False
}

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
        
        if start_date:
            payload['start_date'] = start_date
        if end_date:
            payload['end_date'] = end_date

        try:            
            async with session.get(url, headers=headers, params=payload) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro HTTP {e.status} para o usuário {user_id} no período {start_date} a {end_date}: {e.message}")
            return []
        except aiohttp.ClientError as e:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro de conexão ou outro erro de cliente para o usuário {user_id} no período {start_date} a {end_date}: {e}")
            return []

async def collect_recent_moodle_logs_for_prediction(email, password, api_base_url, days_to_look_back: int = 30):
    """
    Coleta logs recentes da API para fins de previsão.
    """
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando coleta de logs recentes para previsão (últimos {days_to_look_back} dias)...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_look_back)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    async with aiohttp.ClientSession() as session:
        token = await get_access_token_async(email, password, api_base_url)
        if not token:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Não foi possível obter o token de acesso. Abortando coleta de logs para previsão.")
            return pd.DataFrame()

        users_data = await get_moodle_users_async(token, api_base_url)
        if not users_data:
            print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Não foi possível obter a lista de usuários para previsão.")
            return pd.DataFrame()

        recent_logs = []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        tasks = []
        for user in users_data:
            user_id = user.get('user_id')
            user_name = user.get('name')
            if user_id:
                tasks.append(get_user_logs_async(session, user_id, token, api_base_url, semaphore, start_date_str, end_date_str))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            user_info = users_data[i]
            user_id = user_info.get('user_id')
            user_name = user_info.get('name')
            
            if isinstance(res, Exception):
                print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao coletar logs recentes para o usuário {user_id}: {res}")
            elif res:
                for log in res:
                    log['user_id'] = user_id
                    log['user_name'] = user_name
                    log['user_lastaccess'] = user_info.get('user_lastaccess')
                    recent_logs.append(log)
    
    df_recent_logs = pd.DataFrame(recent_logs)
    print(f"DEBUG PREDICT: [{datetime.now()}] Total de logs recentes coletados para previsão: {len(df_recent_logs)}")
    
    if not df_recent_logs.empty:
        df_recent_logs['date'] = pd.to_datetime(df_recent_logs['date'], errors='coerce')
        if pd.api.types.is_string_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], errors='coerce')
        elif pd.api.types.is_numeric_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], unit='s', errors='coerce')
            
        df_recent_logs = df_recent_logs.dropna(subset=['date'])
        if 'course_fullname' not in df_recent_logs.columns:
            df_recent_logs['course_fullname'] = 'Curso Desconhecido'
        if 'eventname' not in df_recent_logs.columns:
            df_recent_logs['eventname'] = 'Evento Desconhecido'
        if 'action' not in df_recent_logs.columns:
            df_recent_logs['action'] = 'Ação Desconhecida'

    return df_recent_logs


async def run_evasion_prediction():
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando o processo de previsão de evasão...")

    # 1. Carregar o modelo e a lista de features (ainda do LOCAL_DATA_DIR)
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURES_PATH):
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Arquivos do modelo ('{MODEL_FILENAME}') ou de features ('{FEATURES_FILENAME}') não encontrados em '{LOCAL_DATA_DIR}'.")
        print(f"DEBUG PREDICT: [{datetime.now()}] Certifique-se de ter executado 'process_evasion_data.py' para treinar e salvar o modelo.")
        return

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, 'r') as f:
        model_features = json.load(f)
    print(f"DEBUG PREDICT: [{datetime.now()}] Modelo e lista de features carregados. Features esperadas: {model_features}")

    # --- MODIFICAÇÃO AQUI: CARREGAR LOGS DO CACHE EM VEZ DE COLETAR NOVAMENTE ---
    print(f"DEBUG PREDICT: [{datetime.now()}] Carregando logs brutos do cache para previsão: {RAW_LOGS_CACHE_FILE}...")
    if not os.path.exists(RAW_LOGS_CACHE_FILE):
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro: Arquivo de cache de logs brutos '{RAW_LOGS_CACHE_FILE}' não encontrado.")
        print(f"DEBUG PREDICT: [{datetime.now()}] Por favor, execute 'collect_raw_logs.py' (ou a função de coleta de logs da API) para gerar este arquivo.")
        return pd.DataFrame() # Retorna um DataFrame vazio se o cache não existir

    try:
        df_raw_logs_for_prediction = pd.read_pickle(RAW_LOGS_CACHE_FILE)
        print(f"DEBUG PREDICT: [{datetime.now()}] Logs brutos carregados do cache. Total de logs: {len(df_raw_logs_for_prediction)}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao carregar logs brutos do cache '{RAW_LOGS_CACHE_FILE}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro de carregamento

    if df_raw_logs_for_prediction.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum log disponível no cache para previsão. Abortando.")
        return

    print("DEBUG PREDICT: Logs brutos carregados (amostra):")
    print(df_raw_logs_for_prediction.head())
    
    # 3. Processar os dados brutos para extrair as mesmas features
    print(f"DEBUG PREDICT: [{datetime.now()}] Iniciando processamento de features para evasão...")
    df_features_for_prediction = process_moodle_logs_for_evasion(df_raw_logs_for_prediction, inactivity_threshold_days=30)
    print(f"DEBUG PREDICT: [{datetime.now()}] Processamento de features concluído.")

    print(f"DEBUG PREDICT: [{datetime.now()}] Total de entradas de features (alunos x cursos): {len(df_features_for_prediction)}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Amostra de features geradas:\n{df_features_for_prediction.head()}")
    
    # Debug prints para as features, conforme solicitado anteriormente
    print(f"DEBUG PREDICT: [{datetime.now()}] Colunas em df_features_for_prediction: {df_features_for_prediction.columns.tolist()}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Amostra de df_features_for_prediction antes do calculador de risco:")
    print(df_features_for_prediction.head().to_string())
    if 'days_since_last_access_global' in df_features_for_prediction.columns:
        print(f"DEBUG PREDICT: [{datetime.now()}] Média e Máx de days_since_last_access_global: {df_features_for_prediction['days_since_last_access_global'].mean()} / {df_features_for_prediction['days_since_last_access_global'].max()}")
    if 'is_in_first_activity_cycle_no_submission' in df_features_for_prediction.columns:
        print(f"DEBUG PREDICT: [{datetime.now()}] Contagem de is_in_first_activity_cycle_no_submission True: {df_features_for_prediction['is_in_first_activity_cycle_no_submission'].sum()}")
    
    if df_features_for_prediction.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum feature processada para previsão. DataFrame de features vazio.")
        return

    # SALVAR df_features_for_prediction AQUI para o app.py consumir
    try:
        df_features_for_prediction.to_csv(APP_FEATURES_FILE, index=False, encoding='utf-8')
        print(f"DEBUG PREDICT: [{datetime.now()}] Features processadas salvas para o app.py em: {APP_FEATURES_FILE}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao salvar features processadas: {e}")
    
    # Preparar as features para a previsão do modelo de ML
    # Certifique-se de que todas as colunas esperadas pelo modelo estão presentes, preenchendo com 0 se ausentes
    for feature in model_features:
        if feature not in df_features_for_prediction.columns:
            df_features_for_prediction[feature] = 0
    X_predict = df_features_for_prediction[model_features].fillna(0)


    # 4. Realizar a Previsão do Modelo de ML
    print(f"DEBUG PREDICT: [{datetime.now()}] Realizando previsões para {len(X_predict)} entradas com o modelo de ML...")
    predictions = model.predict(X_predict)
    prediction_probabilities = model.predict_proba(X_predict)[:, 1]
    
    # Adicionar as previsões ao DataFrame de features
    df_features_for_prediction['predicted_evaded_ml'] = predictions
    df_features_for_prediction['evasion_probability_ml'] = prediction_probabilities

    # 5. Calcular o score de risco baseado em regras usando evasion_risk_calculator
    print(f"DEBUG PREDICT: [{datetime.now()}] Calculando scores de risco baseados em regras...")

    # LISTA COMPLETA DE COLUNAS QUE evasion_risk_calculator.py ESPERA
    cols_for_rule_based = [
        'user_id', 'user_name', 'course_id', 'course_fullname', 'course_category_name',
        'days_since_last_access_global',
        'days_since_last_access_course',
        'total_actions_global',
        'course_total_actions',
        'global_forum_posts_count',
        'global_quiz_attempts_count',
        'is_in_first_activity_cycle_no_submission',
        'has_recent_visual_interaction_in_cycle',
        'unique_resource_types_accessed_course',
        'has_falling_trend_90_days',
        'has_main_exam_submission' # Esta feature deve ser gerada em feature_engineering.py
    ]
    
    # Garante que apenas as colunas necessárias e existentes sejam selecionadas
    # E adiciona as colunas ausentes com valores padrão (False para booleanos, 0 para numéricos)
    df_for_rule_based = df_features_for_prediction.copy()
    for col in cols_for_rule_based:
        if col not in df_for_rule_based.columns:
            if col in ['is_in_first_activity_cycle_no_submission', 'has_recent_visual_interaction_in_cycle', 
                        'has_falling_trend_90_days', 'has_main_exam_submission']:
                df_for_rule_based[col] = False
            elif col in ['days_since_last_access_global', 'days_since_last_access_course',
                          'total_actions_global', 'course_total_actions', 'global_forum_posts_count',
                          'global_quiz_attempts_count', 'unique_resource_types_accessed_course']:
                df_for_rule_based[col] = 0
            else:
                df_for_rule_based[col] = None # Para outras colunas não mapeadas

    df_for_rule_based = df_for_rule_based[cols_for_rule_based] # Seleciona as colunas na ordem correta

    print(f"DEBUG PREDICT: [{datetime.now()}] DataFrame passado para calculate_evasion_risk_scores (amostra):\n{df_for_rule_based.head().to_string()}")
    print(f"DEBUG PREDICT: [{datetime.now()}] Colunas do DataFrame passado para calculate_evasion_risk_scores: {df_for_rule_based.columns.tolist()}")


    df_rule_based_risks = calculate_evasion_risk_scores(df_for_rule_based)

    if df_rule_based_risks.empty:
        print(f"DEBUG PREDICT: [{datetime.now()}] Nenhum score de risco baseado em regras gerado. Abortando salvamento de risk_scores_cache.")
        return

    # 6. Combinar os resultados:
    df_final_risk_scores = pd.merge(
        df_rule_based_risks,
        df_features_for_prediction[['user_id', 'course_fullname', 'predicted_evaded_ml', 'evasion_probability_ml']],
        on=['user_id', 'course_fullname'],
        how='left'
    )
    
    final_columns = [
        'user_id',
        'user_name',
        'course_fullname',
        'overall_evasion_score',
        'is_at_risk',
        'evasion_reasons',
        'predicted_evaded_ml',
        'evasion_probability_ml'
    ]
    
    df_risk_scores_to_save = df_final_risk_scores[final_columns]

    # 7. Salvar o DataFrame de scores de risco completo para o CACHE_DIR com o nome esperado pelo app.py
    try:
        df_risk_scores_to_save.to_csv(APP_RISK_SCORES_FILE, index=False, encoding='utf-8')
        print(f"DEBUG PREDICT: [{datetime.now()}] Scores de risco detalhados salvos para o app.py em: {APP_RISK_SCORES_FILE}")
    except Exception as e:
        print(f"DEBUG PREDICT: [{datetime.now()}] Erro ao salvar '{APP_RISK_SCORES_FILE}': {e}")


    print(f"DEBUG PREDICT: [{datetime.now()}] Processo de previsão de evasão concluído.")

# Bloco de execução principal para predict_evasion.py
if __name__ == '__main__':
    asyncio.run(run_evasion_prediction())
