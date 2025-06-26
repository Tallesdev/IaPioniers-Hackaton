# app.py
from flask import Flask, jsonify, request, current_app
import pandas as pd
import os
import json
import logging
from datetime import datetime
# Importar joblib se você tem certeza que RAW_LOGS_CACHE.pkl é salvo com joblib.dump
# Caso contrário, pd.read_pickle é preferível para arquivos .pkl gerados por pandas.
# Para compatibilidade, manterei pd.read_pickle conforme minha recomendação anterior.
# import joblib 

# Importar Blueprints
from routes.professor_routes import professor_bp
from routes.evasion_report_routes import evasion_report_bp
from routes.status_routes import status_bp
from routes.student_routes import student_bp


# Configuração do Logger
# Ajuste o nível para INFO para logs menos verbosos em execução normal, DEBUG para depuração profunda.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Ou para logs mais detalhados com timestamp:
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


app = Flask(__name__)

# Definir diretórios base (consistentes com os scripts de previsão)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data') # Para arquivos de configuração/mapeamento estáticos (como professor_curso_mapping.json)
CACHE_DIR = os.path.join(BASE_DIR, 'cache') # Para arquivos de cache gerados pelos scripts de ML
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data') # Para arquivos do modelo em predict_evasion.py, e raw_logs_cache.pkl

# Criar diretórios se não existirem
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOCAL_DATA_DIR, exist_ok=True) 

# Caminhos dos arquivos de cache que o app.py consome
PROCESSED_DATA_FILE = os.path.join(CACHE_DIR, 'processed_evasion_data.csv')
RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')
FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv')
PROFESSOR_MAPPING_FILE = os.path.join(DATA_DIR, 'professor_curso_mapping.json')
RAW_LOGS_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl') # Caminho para o cache de logs brutos

# Variáveis de cache globais (serão preenchidas pela função load_data_to_cache)
app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame() # Inicia com DataFrame vazio
app.config['RISK_SCORES_CACHE'] = pd.DataFrame()
app.config['FEATURES_CACHE'] = pd.DataFrame()
app.config['PROFESSOR_COURSE_MAPPING'] = {} # Inicia com dicionário vazio
app.config['RAW_LOGS_CACHE'] = pd.DataFrame() # Inicia com DataFrame vazio

def load_data_to_cache():
    """Carrega os dados processados e de risco de evasão para o cache da aplicação."""
    app.logger.info(f"[{datetime.now()}] Tentando carregar dados para o cache...")
    
    # Carregar RAW_LOGS_CACHE
    if os.path.exists(RAW_LOGS_FILE):
        try:
            # Preferir pd.read_pickle para arquivos .pkl gerados por pandas
            app.config['RAW_LOGS_CACHE'] = pd.read_pickle(RAW_LOGS_FILE)
            app.logger.info(f"[{datetime.now()}] '{RAW_LOGS_FILE}' carregado com sucesso. {len(app.config['RAW_LOGS_CACHE'])} linhas.")
            
            # Garante que 'time_dt' existe e é do tipo datetime
            if 'time_dt' not in app.config['RAW_LOGS_CACHE'].columns or \
               not pd.api.types.is_datetime64_any_dtype(app.config['RAW_LOGS_CACHE']['time_dt']):
                app.logger.info(f"[{datetime.now()}] Coluna 'time_dt' não encontrada ou não é datetime. Tentando criar/converter...")
                if 'time' in app.config['RAW_LOGS_CACHE'].columns:
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['time'], unit='s', errors='coerce')
                elif 'date' in app.config['RAW_LOGS_CACHE'].columns:
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['date'], errors='coerce')
                else:
                    app.logger.warning(f"[{datetime.now()}] Nenhuma coluna 'time' ou 'date' encontrada para criar 'time_dt' no RAW_LOGS_CACHE.")
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.NaT # Define como Not a Time se não encontrar
            
            # Remover linhas com NaT em 'time_dt' após a conversão
            original_rows = len(app.config['RAW_LOGS_CACHE'])
            app.config['RAW_LOGS_CACHE'].dropna(subset=['time_dt'], inplace=True)
            if len(app.config['RAW_LOGS_CACHE']) < original_rows:
                app.logger.warning(f"[{datetime.now()}] {original_rows - len(app.config['RAW_LOGS_CACHE'])} linhas removidas de RAW_LOGS_CACHE devido a 'time_dt' inválido.")

        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar ou processar '{RAW_LOGS_FILE}': {e}", exc_info=True)
            app.config['RAW_LOGS_CACHE'] = pd.DataFrame() # Define como DataFrame vazio em caso de erro
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{RAW_LOGS_FILE}' não encontrado. Execute 'collect_raw_logs.py' para coletar logs brutos.")
        app.config['RAW_LOGS_CACHE'] = pd.DataFrame()

    # Carregar df_processed_data (de process_evasion_data.py) - Mantenha se for usado em alguma rota
    if os.path.exists(PROCESSED_DATA_FILE):
        try:
            app.config['PROCESSED_DATA_CACHE'] = pd.read_csv(PROCESSED_DATA_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{PROCESSED_DATA_FILE}' carregado com sucesso. {len(app.config['PROCESSED_DATA_CACHE'])} linhas.")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{PROCESSED_DATA_FILE}': {e}", exc_info=True)
            app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{PROCESSED_DATA_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py'.")
        app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()

    # Carregar df_risk_scores_cache (de evasion_predictions_detailed.csv)
    if os.path.exists(RISK_SCORES_FILE):
        try:
            app.config['RISK_SCORES_CACHE'] = pd.read_csv(RISK_SCORES_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{RISK_SCORES_FILE}' carregado com sucesso. {len(app.config['RISK_SCORES_CACHE'])} linhas.")
            app.logger.debug(f"Colunas de RISK_SCORES_CACHE: {app.config['RISK_SCORES_CACHE'].columns.tolist()}")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{RISK_SCORES_FILE}': {e}", exc_info=True)
            app.config['RISK_SCORES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{RISK_SCORES_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py' ou 'predict_evasion.py'.")
        app.config['RISK_SCORES_CACHE'] = pd.DataFrame()

    # Carregar df_features_cache (de student_features.csv)
    if os.path.exists(FEATURES_FILE):
        try:
            app.config['FEATURES_CACHE'] = pd.read_csv(FEATURES_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{FEATURES_FILE}' carregado com sucesso. {len(app.config['FEATURES_CACHE'])} linhas.")
            app.logger.debug(f"Colunas de FEATURES_CACHE: {app.config['FEATURES_CACHE'].columns.tolist()}")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{FEATURES_FILE}': {e}", exc_info=True)
            app.config['FEATURES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{FEATURES_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py'.")
        app.config['FEATURES_CACHE'] = pd.DataFrame()

    # Carregar mapeamento professor-curso
    if os.path.exists(PROFESSOR_MAPPING_FILE):
        try:
            with open(PROFESSOR_MAPPING_FILE, 'r', encoding='utf-8') as f:
                app.config['PROFESSOR_COURSE_MAPPING'] = json.load(f)
            app.logger.info(f"[{datetime.now()}] '{PROFESSOR_MAPPING_FILE}' carregado com sucesso. {len(app.config['PROFESSOR_COURSE_MAPPING'])} entradas.")
            app.logger.debug(f"PROFESSOR_COURSE_MAPPING keys: {list(app.config['PROFESSOR_COURSE_MAPPING'].keys())[:5]}")
        except json.JSONDecodeError as e:
            app.logger.error(f"[{datetime.now()}] Erro de decodificação JSON ao carregar '{PROFESSOR_MAPPING_FILE}': {e}", exc_info=True)
            app.config['PROFESSOR_COURSE_MAPPING'] = {}
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{PROFESSOR_MAPPING_FILE}': {e}", exc_info=True)
            app.config['PROFESSOR_COURSE_MAPPING'] = {}
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo de mapeamento de professor-curso não encontrado: {PROFESSOR_MAPPING_FILE}. Crie este arquivo para habilitar filtros por professor.")
        app.config['PROFESSOR_COURSE_MAPPING'] = {}

# Carregar dados quando a aplicação for iniciada (executado uma vez na inicialização)
with app.app_context():
    load_data_to_cache()

# Rotas principais
@app.route('/')
def index():
    return "API de Monitoramento de Evasão UNIFENAS - Acesse /api/professor/dashboard-data ou /api/status/status"

@app.route('/health')
def health_check():
    """Verifica o status dos caches de dados."""
    status = {
        "status": "ok",
        "raw_logs_loaded": not app.config['RAW_LOGS_CACHE'].empty,
        "risk_scores_loaded": not app.config['RISK_SCORES_CACHE'].empty,
        "features_loaded": not app.config['FEATURES_CACHE'].empty,
        "professor_course_mapping_loaded": bool(app.config['PROFESSOR_COURSE_MAPPING']), # Verifica se o dicionário não está vazio
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(status)

# REGISTRAR BLUEPRINT DE PROFESSOR (COM PREFIXO DE URL)
app.register_blueprint(professor_bp)
app.register_blueprint(evasion_report_bp)
app.register_blueprint(student_bp)
app.register_blueprint(status_bp)

if __name__ == '__main__':
    # Este é um servidor de desenvolvimento, não recomendado para produção
    app.run(debug=True, host='0.0.0.0', port=5000)
