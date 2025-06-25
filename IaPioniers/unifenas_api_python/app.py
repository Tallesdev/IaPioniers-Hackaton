# app.py
from flask import Flask, jsonify, request, current_app
import pandas as pd
import os
import json
import logging
from datetime import datetime
import joblib # Importar joblib para carregar .pkl

# Importar Blueprints
from routes.professor_routes import professor_bp
from routes.evasion_report_routes import evasion_report_bp
from routes.status_routes import status_bp
from routes.student_routes import student_bp


# Configuração do Logger
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

app = Flask(__name__)

# Definir diretórios base (consistentes com os scripts de previsão)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data') # Para arquivos de configuração/mapeamento estáticos (como professor_curso_mapping.json)
CACHE_DIR = os.path.join(BASE_DIR, 'cache') # Para arquivos de cache gerados pelos scripts de ML
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data') # Para arquivos do modelo em predict_evasion.py

# Criar diretórios se não existirem
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOCAL_DATA_DIR, exist_ok=True) # Criar também o local_data aqui para consistência

# Caminhos dos arquivos de cache que o app.py consome
PROCESSED_DATA_FILE = os.path.join(CACHE_DIR, 'processed_evasion_data.csv') # Gerado por process_evasion_data.py
RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv') # Gerado por predict_evasion.py
FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv') # Gerado por process_evasion_data.py
PROFESSOR_MAPPING_FILE = os.path.join(DATA_DIR, 'professor_curso_mapping.json') # Arquivo de mapeamento manual
RAW_LOGS_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl') # <-- DEFINIÇÃO ADICIONADA AQUI

# Variáveis de cache globais (serão preenchidas pela função load_data_to_cache)
app.config['PROCESSED_DATA_CACHE'] = None
app.config['RISK_SCORES_CACHE'] = None
app.config['FEATURES_CACHE'] = None
app.config['PROFESSOR_COURSE_MAPPING'] = None
app.config['RAW_LOGS_CACHE'] = None # <-- INICIALIZAÇÃO ADICIONADA AQUI

def load_data_to_cache():
    """Carrega os dados processados e de risco de evasão para o cache da aplicação."""
    app.logger.info(f"[{datetime.now()}] Tentando carregar dados para o cache...")
    
    # Carregar RAW_LOGS_CACHE
    if os.path.exists(RAW_LOGS_FILE):
        try:
            app.config['RAW_LOGS_CACHE'] = joblib.load(RAW_LOGS_FILE)
            app.logger.info(f"[{datetime.now()}] '{RAW_LOGS_FILE}' carregado com sucesso. {len(app.config['RAW_LOGS_CACHE'])} linhas.")
            # Opcional: garantir tipos de colunas essenciais, como 'date' ou 'time' se for datetime/numérico
            if 'time' in app.config['RAW_LOGS_CACHE'].columns:
                app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['time'], unit='s', errors='coerce')
            elif 'date' in app.config['RAW_LOGS_CACHE'].columns:
                app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['date'], errors='coerce')
            
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{RAW_LOGS_FILE}': {e}")
            app.config['RAW_LOGS_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{RAW_LOGS_FILE}' não encontrado. Execute 'collect_raw_logs.py' para coletar logs brutos.")
        app.config['RAW_LOGS_CACHE'] = pd.DataFrame()

    # Carregar df_processed_data (de process_evasion_data.py)
    if os.path.exists(PROCESSED_DATA_FILE):
        try:
            app.config['PROCESSED_DATA_CACHE'] = pd.read_csv(PROCESSED_DATA_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{PROCESSED_DATA_FILE}' carregado com sucesso. {len(app.config['PROCESSED_DATA_CACHE'])} linhas.")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{PROCESSED_DATA_FILE}': {e}")
            app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame() # Atribui DataFrame vazio em caso de erro
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{PROCESSED_DATA_FILE}' não encontrado. Execute 'process_evasion_data.py'.")
        app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()

    # Carregar df_risk_scores_cache (de predict_evasion.py)
    if os.path.exists(RISK_SCORES_FILE):
        try:
            app.config['RISK_SCORES_CACHE'] = pd.read_csv(RISK_SCORES_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{RISK_SCORES_FILE}' carregado com sucesso. {len(app.config['RISK_SCORES_CACHE'])} linhas.")
            app.logger.debug(f"Colunas de RISK_SCORES_CACHE: {app.config['RISK_SCORES_CACHE'].columns.tolist()}")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{RISK_SCORES_FILE}': {e}")
            app.config['RISK_SCORES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{RISK_SCORES_FILE}' não encontrado. Execute 'predict_evasion.py'.")
        app.config['RISK_SCORES_CACHE'] = pd.DataFrame()

    # Carregar df_features_cache (de process_evasion_data.py)
    if os.path.exists(FEATURES_FILE):
        try:
            # Assumindo que student_features.csv é salvo como CSV, não PKL.
            app.config['FEATURES_CACHE'] = pd.read_csv(FEATURES_FILE, encoding='utf-8')
            app.logger.info(f"[{datetime.now()}] '{FEATURES_FILE}' carregado com sucesso. {len(app.config['FEATURES_CACHE'])} linhas.")
            app.logger.debug(f"Colunas de FEATURES_CACHE: {app.config['FEATURES_CACHE'].columns.tolist()}")
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{FEATURES_FILE}': {e}")
            app.config['FEATURES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"[{datetime.now()}] Arquivo '{FEATURES_FILE}' não encontrado. Execute 'process_evasion_data.py'.")
        app.config['FEATURES_CACHE'] = pd.DataFrame()

    # Carregar mapeamento professor-curso
    if os.path.exists(PROFESSOR_MAPPING_FILE):
        try:
            with open(PROFESSOR_MAPPING_FILE, 'r', encoding='utf-8') as f:
                app.config['PROFESSOR_COURSE_MAPPING'] = json.load(f)
            app.logger.info(f"[{datetime.now()}] '{PROFESSOR_MAPPING_FILE}' carregado com sucesso. {len(app.config['PROFESSOR_COURSE_MAPPING'])} entradas.")
            app.logger.debug(f"PROFESSOR_COURSE_MAPPING keys: {list(app.config['PROFESSOR_COURSE_MAPPING'].keys())[:5]}")
        except json.JSONDecodeError as e:
            app.logger.error(f"[{datetime.now()}] Erro de decodificação JSON ao carregar '{PROFESSOR_MAPPING_FILE}': {e}")
            app.config['PROFESSOR_COURSE_MAPPING'] = {}
        except Exception as e:
            app.logger.error(f"[{datetime.now()}] Erro ao carregar '{PROFESSOR_MAPPING_FILE}': {e}")
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
    return "API de Monitoramento de Evasão UNIFENAS - Acesse /api/professor/course-summaries ou /api/professor-evasion-risk"

@app.route('/health')
def health_check():
    """Verifica o status dos caches de dados."""
    status = {
        "status": "ok",
        "raw_logs_loaded": app.config['RAW_LOGS_CACHE'] is not None and not app.config['RAW_LOGS_CACHE'].empty, # Adicionado aqui
        "risk_scores_loaded": app.config['RISK_SCORES_CACHE'] is not None and not app.config['RISK_SCORES_CACHE'].empty,
        "features_loaded": app.config['FEATURES_CACHE'] is not None and not app.config['FEATURES_CACHE'].empty,
        "professor_course_mapping_loaded": app.config['PROFESSOR_COURSE_MAPPING'] is not None and bool(app.config['PROFESSOR_COURSE_MAPPING']),
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
    app.run(debug=True)