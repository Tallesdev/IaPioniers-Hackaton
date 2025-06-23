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

# Definir diretórios base para consistência
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data') # Para arquivos internos do pipeline (modelo, features do modelo, cache de logs brutos)
CACHE_DIR = os.path.join(BASE_DIR, 'cache') # Para arquivos que a API (app.py) consome

# Criar diretórios se não existirem
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Definição dos caminhos para CARREGAR o modelo e a lista de features (salvos em local_data)
MODEL_FILENAME = 'evasion_model.joblib'
FEATURES_FILENAME = 'model_features.json'
MODEL_PATH = os.path.join(LOCAL_DATA_DIR, MODEL_FILENAME)
FEATURES_PATH = os.path.join(LOCAL_DATA_DIR, FEATURES_FILENAME)

# Caminho para o arquivo de logs brutos em cache (salvo em local_data)
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')

# Caminho para o arquivo de scores de risco que o app.py espera, salvo no CACHE_DIR
APP_RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')


# --- Seções de Configuração para Coleta de Logs ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

# AJUSTES PARA MITIGAR O ERRO 429:
REQUEST_DELAY_SECONDS = 1.5 # Aumentado para 1.5 segundos
MAX_CONCURRENT_REQUESTS = 2 # Reduzido para 2 requisições simultâneas

RETRY_SETTINGS = {
    'stop': stop_after_attempt(10), # Aumentado para 10 tentativas
    'wait': wait_exponential(multiplier=1, min=5, max=180), # min para 5s, max para 3 minutos
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': False # Permite que a exceção seja capturada e o processo continue
}

# --- Funções Assíncronas para a API Moodle ---
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
            # A retry function _fetch_single_log_with_retry já está decorada com @retry(**RETRY_SETTINGS)
            # e tem reraise=False, então a exceção 429 será capturada pelo bloco except externo
            # após todas as tentativas falharem.
            async with session.get(url, headers=headers, params=payload) as response:
                response.raise_for_status() # Lança ClientResponseError para 4xx/5xx
                return await response.json()
        except aiohttp.ClientResponseError as e: # Capture aiohttp.ClientResponseError especificamente
            print(f"[{datetime.now()}] Erro HTTP {e.status} para o usuário {user_id} no período {start_date} a {end_date}: {e.message}")
            return [] # Retorna lista vazia para indicar falha e continuar
        except aiohttp.ClientError as e: # Para outros erros de cliente aiohttp (conexão, etc.)
            print(f"[{datetime.now()}] Erro de conexão ou outro erro de cliente para o usuário {user_id} no período {start_date} a {end_date}: {e}")
            return []

async def collect_recent_moodle_logs_for_prediction(email, password, api_base_url, days_to_look_back: int = 30):
    """
    Coleta logs recentes da API para fins de previsão.
    """
    print(f"[{datetime.now()}] Iniciando coleta de logs recentes para previsão (últimos {days_to_look_back} dias)...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_look_back)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    async with aiohttp.ClientSession() as session:
        token = await get_access_token_async(email, password, api_base_url)
        if not token:
            print(f"[{datetime.now()}] Erro: Não foi possível obter o token de acesso. Abortando coleta de logs para previsão.")
            return pd.DataFrame()

        users_data = await get_moodle_users_async(token, api_base_url)
        if not users_data:
            print(f"[{datetime.now()}] Erro: Não foi possível obter a lista de usuários para previsão.")
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
                print(f"[{datetime.now()}] Erro ao coletar logs recentes para o usuário {user_id}: {res}")
            elif res:
                for log in res:
                    log['user_id'] = user_id
                    log['user_name'] = user_name
                    log['user_lastaccess'] = user_info.get('user_lastaccess')
                    recent_logs.append(log)
    
    df_recent_logs = pd.DataFrame(recent_logs)
    print(f"[{datetime.now()}] Total de logs recentes coletados para previsão: {len(df_recent_logs)}")
    
    if not df_recent_logs.empty:
        df_recent_logs['date'] = pd.to_datetime(df_recent_logs['date'], errors='coerce')
        if pd.api.types.is_string_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], errors='coerce')
        elif pd.api.types.is_numeric_dtype(df_recent_logs['user_lastaccess']):
            df_recent_logs['user_lastaccess'] = pd.to_datetime(df_recent_logs['user_lastaccess'], unit='s', errors='coerce')
        
        df_recent_logs = df_recent_logs.dropna(subset=['date'])
        if 'course_fullname' not in df_recent_logs.columns:
            df_recent_logs['course_fullname'] = 'Curso Desconhecido'
        # Adicionar 'eventname' e 'action' com valores padrão se não existirem
        if 'eventname' not in df_recent_logs.columns:
            df_recent_logs['eventname'] = 'Evento Desconhecido'
        if 'action' not in df_recent_logs.columns:
            df_recent_logs['action'] = 'Ação Desconhecida'

    return df_recent_logs

async def run_evasion_prediction():
    print(f"[{datetime.now()}] Iniciando o processo de previsão de evasão...")

    # 1. Carregar o modelo e a lista de features (do LOCAL_DATA_DIR, onde process_evasion_data.py salva)
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURES_PATH):
        print(f"[{datetime.now()}] Erro: Arquivos do modelo ('{MODEL_FILENAME}') ou de features ('{FEATURES_FILENAME}') não encontrados em '{LOCAL_DATA_DIR}'.")
        print(f"[{datetime.now()}] Certifique-se de ter executado 'process_evasion_data.py' para treinar e salvar o modelo.")
        return

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, 'r') as f:
        model_features = json.load(f)
    print(f"[{datetime.now()}] Modelo e lista de features carregados. Features esperadas: {model_features}")

    # 2. Obter os novos dados para previsão (Chamando a função de coleta de logs recentes)
    df_raw_logs_for_prediction = await collect_recent_moodle_logs_for_prediction(
        UNIFENAS_EMAIL, UNIFENAS_PASSWORD, MOODLE_API_BASE_URL, days_to_look_back=30
    )

    if df_raw_logs_for_prediction.empty:
        print(f"[{datetime.now()}] Nenhum log recente disponível para previsão. Abortando.")
        return

    print("\nLogs recentes coletados (amostra):")
    print(df_raw_logs_for_prediction.head())
    
    # 3. Processar os novos dados para extrair as mesmas features
    df_features_for_prediction = process_moodle_logs_for_evasion(df_raw_logs_for_prediction, inactivity_threshold_days=30)

    if df_features_for_prediction.empty:
        print(f"[{datetime.now()}] Nenhum feature processada para previsão. DataFrame de features vazio.")
        return

    # Prepare X_predict usando as features esperadas pelo modelo
    missing_features = [f for f in model_features if f not in df_features_for_prediction.columns]
    if missing_features:
        print(f"[{datetime.now()}] Erro: Features esperadas pelo modelo ausentes nos dados processados: {missing_features}")
        return

    X_predict = df_features_for_prediction[model_features] # Corrigido: Definição de X_predict

    # 4. Realizar a Previsão do Modelo de ML
    print(f"[{datetime.now()}] Realizando previsões para {len(X_predict)} entradas com o modelo de ML...")
    predictions = model.predict(X_predict)
    prediction_probabilities = model.predict_proba(X_predict)[:, 1] # Probabilidade da classe positiva (evadido)
    
    # Adicionar as previsões ao DataFrame de features
    df_features_for_prediction['predicted_evaded_ml'] = predictions # Renomeado para evitar conflito com is_at_risk do rule-based
    df_features_for_prediction['evasion_probability_ml'] = prediction_probabilities # Renomeado

    # 5. Calcular o score de risco baseado em regras usando evasion_risk_calculator
    print(f"[{datetime.now()}] Calculando scores de risco baseados em regras...")

    # Colunas que calculate_evasion_risk_scores precisa e que queremos no resultado final
    cols_for_rule_based = [
        'user_id', 'user_name', 'course_fullname', 
        'overall_last_access_days_ago', 'course_last_activity_days_ago',
        'course_activity_count', 'course_unique_actions',
        'course_activity_duration_days'
        # Você precisará adicionar outras colunas aqui se evasion_risk_calculator.py precisar delas
        # como 'global_forum_posts_count', 'global_quiz_attempts_count', etc.
        # Caso contrário, pode causar KeyError no evasion_risk_calculator
    ]
    
    # Filtra o DataFrame de features para ter apenas as colunas que serão usadas no cálculo de risco baseado em regras
    # e as colunas de identificação.
    # Adiciona verificação para garantir que todas as colunas existem antes de selecionar
    missing_cols_for_rules = [col for col in cols_for_rule_based if col not in df_features_for_prediction.columns]
    if missing_cols_for_rules:
        print(f"[{datetime.now()}] AVISO: As seguintes colunas esperadas para cálculo de risco baseado em regras não foram encontradas: {missing_cols_for_rules}. Isso pode afetar o cálculo de risco.")
        # Se você quiser que o script falhe aqui, mude o AVISO para ERRO e adicione 'return'
        # ou adicione lógica para preencher essas colunas com valores padrão (0 ou False)

    # Seleciona as colunas, tratando as ausentes para evitar erros (preenche com 0, por exemplo)
    df_for_rule_based = df_features_for_prediction[[col for col in cols_for_rule_based if col in df_features_for_prediction.columns]].copy()
    # Para as colunas que faltam, adicione-as com um valor padrão para que calculate_evasion_risk_scores não quebre
    for col in missing_cols_for_rules:
        if col in ['global_forum_posts_count', 'global_quiz_attempts_count', 'unique_resource_types_accessed_course', 'total_actions_global', 'course_total_actions']:
            df_for_rule_based[col] = 0
        elif col in ['is_in_first_activity_cycle_no_submission', 'has_recent_visual_interaction_in_cycle', 'has_falling_trend_90_days']:
            df_for_rule_based[col] = False


    df_rule_based_risks = calculate_evasion_risk_scores(df_for_rule_based)

    if df_rule_based_risks.empty:
        print(f"[{datetime.now()}] Nenhum score de risco baseado em regras gerado. Abortando salvamento de risk_scores_cache.")
        return

    # 6. Combinar os resultados:
    # Mescla as previsões do ML ao DataFrame de riscos baseado em regras
    # A mesclagem deve ser feita por user_id e course_fullname para garantir a unicidade
    df_final_risk_scores = pd.merge(
        df_rule_based_risks,
        df_features_for_prediction[['user_id', 'course_fullname', 'predicted_evaded_ml', 'evasion_probability_ml']],
        on=['user_id', 'course_fullname'],
        how='left'
    )

    # Renomear as colunas para o que o app.py espera
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
    
    # Selecionar apenas as colunas finais
    df_risk_scores_to_save = df_final_risk_scores[final_columns]

    # 7. Salvar o DataFrame de scores de risco completo para o CACHE_DIR com o nome esperado pelo app.py
    try:
        df_risk_scores_to_save.to_csv(APP_RISK_SCORES_FILE, index=False, encoding='utf-8')
        print(f"[{datetime.now()}] Scores de risco detalhados salvos para o app.py em: {APP_RISK_SCORES_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Erro ao salvar '{APP_RISK_SCORES_FILE}': {e}")

    print(f"[{datetime.now()}] Processo de previsão de evasão concluído.")

# Bloco de execução principal para predict_evasion.py
if __name__ == '__main__':
    asyncio.run(run_evasion_prediction())