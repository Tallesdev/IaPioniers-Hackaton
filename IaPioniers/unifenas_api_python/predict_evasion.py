# predict_evasion.py
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp # Se for coletar logs da API diretamente aqui
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import joblib

# Importar as funções de processamento de features do process_evasion_data.py
from process_evasion_data import process_moodle_logs_for_evasion

# Importar a função de cálculo de risco do evasion_risk_calculator.py
from evasion_risk_calculator import calculate_evasion_risk_scores # ADICIONAR ESTA LINHA

# Definir diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data') # Para arquivos internos do pipeline (modelo, features do modelo, cache interno de logs)
CACHE_DIR = os.path.join(BASE_DIR, 'cache') # Para arquivos que a API (app.py) consome

# Criar diretórios se não existirem
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


# Definição do caminho do cache e do modelo (para carregamento)
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')
# FEATURES_ONLY_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'features_only_cache.pkl') # Esta linha pode ser removida
# RISK_SCORES_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'risk_scores_cache.pkl') # Esta linha pode ser removida se só for salvar CSV

MODEL_FILENAME = 'evasion_model.joblib'
FEATURES_FILENAME = 'model_features.json'
# Caminhos corretos para carregar o modelo e features da pasta local_data
MODEL_PATH = os.path.join(LOCAL_DATA_DIR, MODEL_FILENAME)
FEATURES_PATH = os.path.join(LOCAL_DATA_DIR, FEATURES_FILENAME)

# Caminho para o arquivo de scores de risco que o app.py espera, salvo no CACHE_DIR
APP_RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')

# Definição do caminho do cache para features (adicione este)
APP_FEATURES_FILE = os.path.join(LOCAL_DATA_DIR, 'features_data_for_app.pkl') # Ou CSV, mas PKL é mais eficiente para DataFrames


# --- Seções de Configuração para Coleta de Logs ---
# --- Seções de Configuração para Coleta de Logs ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

# AJUSTES MAIS AGRESSIVOS AQUI:
REQUEST_DELAY_SECONDS = 1.5 # Aumentado para 1.5 segundos (ou até 2.0 se necessário)
MAX_CONCURRENT_REQUESTS = 2 # Reduzido para 2 requisições simultâneas (muito conservador, mas para testar)

RETRY_SETTINGS = {
    'stop': stop_after_attempt(10), # Aumente mais as tentativas
    'wait': wait_exponential(multiplier=1, min=5, max=180), # min para 5s, max para 3 minutos
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': False # Manter como False
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
        # Este delay agora é *dentro* do semáforo, garantindo que mesmo requisições concorrentes
        # respeitem um tempo mínimo entre si para cada "slot" do semáforo.
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

    # 1. Carregar o modelo e a lista de features (ainda do LOCAL_DATA_DIR)
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURES_PATH):
        print(f"[{datetime.now()}] Erro: Arquivos do modelo ('{MODEL_FILENAME}') ou de features ('{FEATURES_FILENAME}') não encontrados em '{LOCAL_DATA_DIR}'.")
        print(f"[{datetime.now()}] Certifique-se de ter executado 'process_evasion_data.py' para treinar e salvar o modelo.")
        return

    model = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, 'r') as f:
        model_features = json.load(f)
    print(f"[{datetime.now()}] Modelo e lista de features carregados. Features esperadas: {model_features}")

    # 2. Obter os novos dados para previsão (Chamando a nova função de coleta de logs recentes)
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

    # SALVAR df_features_for_prediction AQUI para o app.py consumir
    try:
        df_features_for_prediction.to_pickle(APP_FEATURES_FILE) # Ou .to_csv se preferir CSV
        print(f"[{datetime.now()}] Features processadas salvas para o app.py em: {APP_FEATURES_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Erro ao salvar features processadas: {e}")
    # ...

    # 4. Realizar a Previsão do Modelo de ML
    print(f"[{datetime.now()}] Realizando previsões para {len(X_predict)} entradas com o modelo de ML...")
    predictions = model.predict(X_predict)
    prediction_probabilities = model.predict_proba(X_predict)[:, 1] # Probabilidade da classe positiva (evadido)
    
    # Adicionar as previsões ao DataFrame de features
    df_features_for_prediction['predicted_evaded_ml'] = predictions # Renomeado para evitar conflito com is_at_risk do rule-based
    df_features_for_prediction['evasion_probability_ml'] = prediction_probabilities # Renomeado

    # 5. Calcular o score de risco baseado em regras usando evasion_risk_calculator
    print(f"[{datetime.now()}] Calculando scores de risco baseados em regras...")

    # *** INÍCIO DA CORREÇÃO ***
    # Antes de chamar calculate_evasion_risk_scores, garanta que as colunas de identificação
    # necessárias para o output final estejam presentes no DataFrame que será passado
    # e que a função as retorne.

    # Precisamos garantir que df_features_for_prediction tenha todas as colunas
    # que calculate_evasion_risk_scores espera e que queremos no output final.
    # As colunas 'user_id', 'user_name', 'course_fullname' são cruciais.
    # A função calculate_evasion_risk_scores usa 'overall_last_access_days_ago'
    # e 'course_last_activity_days_ago' entre outras.
    
    # É fundamental que calculate_evasion_risk_scores mantenha 'user_id', 'user_name', 'course_fullname'
    # em seu resultado final, ou as re-adicione.
    # Vamos passar apenas as colunas necessárias para calculate_evasion_risk_scores
    # e que queremos de volta para a mesclagem.

    # Colunas que calculate_evasion_risk_scores precisa e que queremos no resultado final
    cols_for_rule_based = [
        'user_id', 'user_name', 'course_fullname', 
        'overall_last_access_days_ago', 'course_last_activity_days_ago',
        # Adicione outras features que 'calculate_evasion_risk_scores' usa para suas regras,
        # como 'course_activity_count', 'engagement_per_day', etc.
        'course_activity_count', 'course_unique_actions',
        'course_activity_duration_days'
    ]
    
    # Filtra o DataFrame de features para ter apenas as colunas que serão usadas no cálculo de risco baseado em regras
    # e as colunas de identificação.
    df_for_rule_based = df_features_for_prediction[cols_for_rule_based].copy()

    df_rule_based_risks = calculate_evasion_risk_scores(df_for_rule_based)

    if df_rule_based_risks.empty:
        print(f"[{datetime.now()}] Nenhum score de risco baseado em regras gerado. Abortando salvamento de risk_scores_cache.")
        return

    # 6. Combinar os resultados:
    # O df_rule_based_risks AGORA DEVE CONTER 'user_id', 'user_name', 'course_fullname'
    # pois garantimos que elas foram passadas para calculate_evasion_risk_scores e esperamos que ela as mantenha.
    # Mescla as previsões do ML ao DataFrame de riscos baseado em regras
    # A mesclagem deve ser feita por user_id e course_fullname para garantir a unicidade
    df_final_risk_scores = pd.merge(
        df_rule_based_risks,
        df_features_for_prediction[['user_id', 'course_fullname', 'predicted_evaded_ml', 'evasion_probability_ml']],
        on=['user_id', 'course_fullname'],
        how='left'
    )
    # *** FIM DA CORREÇÃO ***

    # Renomear as colunas para o que o app.py espera, se necessário.
    # App.py espera: 'user_id', 'user_name', 'overall_evasion_score', 'is_at_risk', 'evasion_reasons'
    # 'overall_evasion_score' e 'evasion_reasons' vêm do rule-based.
    # 'is_at_risk' é do rule-based, mas você pode querer uma coluna separada para o ML
    # 'course_fullname' também está lá.
    
    # Para o app.py, vamos manter as colunas que ele espera e adicionar as do ML.
    # É importante que 'overall_evasion_score' e 'is_at_risk' sejam os do rule-based score
    # ou que você decida qual priorizar. Por enquanto, mantemos as do rule-based.
    
    final_columns = [
        'user_id',
        'user_name',
        'course_fullname', # Adicionado explicitamente aqui para garantir
        'overall_evasion_score', # Score baseado em regras
        'is_at_risk', # At-risk baseado em regras
        'evasion_reasons', # Razões baseadas em regras
        'predicted_evaded_ml', # Previsão binária do modelo de ML
        'evasion_probability_ml' # Probabilidade do modelo de ML
    ]
    
    # Selecionar apenas as colunas finais
    df_risk_scores_to_save = df_final_risk_scores[final_columns]

    # 7. Salvar o DataFrame de scores de risco completo para o CACHE_DIR com o nome esperado pelo app.py
    try:
        df_risk_scores_to_save.to_csv(APP_RISK_SCORES_FILE, index=False, encoding='utf-8')
        print(f"[{datetime.now()}] Scores de risco detalhados salvos para o app.py em: {APP_RISK_SCORES_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Erro ao salvar '{APP_RISK_SCORES_FILE}': {e}")

    # A linha abaixo que salva um CSV com timestamp é opcional, mantida para depuração se desejar.
    # output_filename_csv_debug = os.path.join(LOCAL_DATA_DIR, f"evasion_predictions_detailed_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    # df_risk_scores_to_save.to_csv(output_filename_csv_debug, index=False)
    # print(f"[{datetime.now()}] Previsões detalhadas (debug) salvas em CSV: {output_filename_csv_debug}")


    print(f"[{datetime.now()}] Processo de previsão de evasão concluído.")

# Bloco de execução principal para predict_evasion.py
if __name__ == '__main__':
    asyncio.run(run_evasion_prediction())