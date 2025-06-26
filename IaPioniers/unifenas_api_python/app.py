# app.py
from flask import Flask, jsonify, request, current_app
import pandas as pd
import os
import json
import logging
from datetime import datetime

# Importar Blueprints
from routes.professor_routes import professor_bp
from routes.evasion_report_routes import evasion_report_bp
from routes.status_routes import status_bp
from routes.student_routes import student_bp
from routes.course_routes import course_bp
from routes.students_overview_routes import students_overview_bp # NOVA IMPORTAÇÃO

# Importar as constantes de threshold do evasion_risk_calculator.py
# para que possam ser acessadas via app.config
from evasion_risk_calculator import INACTIVITY_THRESHOLD_GLOBAL_DAYS, INACTIVITY_THRESHOLD_COURSE_DAYS, DEFAULT_RISK_THRESHOLD


# Configuração do Logger
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s') # <-- GARANTA QUE ESTÁ EM DEBUG
app = Flask(__name__)

# Definir diretórios base (consistentes com os scripts de previsão)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data')

# Criar diretórios se não existirem
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOCAL_DATA_DIR, exist_ok=True) 

# Caminhos dos arquivos de cache que o app.py consome
PROCESSED_DATA_FILE = os.path.join(CACHE_DIR, 'processed_evasion_data.csv')
RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')
FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv') # Alterado para CSV
PROFESSOR_MAPPING_FILE = os.path.join(DATA_DIR, 'professor_curso_mapping.json')
RAW_LOGS_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')

# Variáveis de cache globais (serão preenchidas pela função load_data_to_cache)
app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()
app.config['RISK_SCORES_CACHE'] = pd.DataFrame()
app.config['FEATURES_CACHE'] = pd.DataFrame()
app.config['PROFESSOR_COURSE_MAPPING'] = {}
app.config['RAW_LOGS_CACHE'] = pd.DataFrame()

# NOVO: Carregar as constantes de threshold para o app.config
app.config['INACTIVITY_THRESHOLD_GLOBAL_DAYS_CONFIG'] = INACTIVITY_THRESHOLD_GLOBAL_DAYS
app.config['INACTIVITY_THRESHOLD_COURSE_DAYS_CONFIG'] = INACTIVITY_THRESHOLD_COURSE_DAYS
app.config['DEFAULT_RISK_THRESHOLD_CONFIG'] = DEFAULT_RISK_THRESHOLD


def load_data_to_cache():
    """Carrega os dados processados e de risco de evasão para o cache da aplicação."""
    app.logger.info(f"APP: [{datetime.now()}] Tentando carregar dados para o cache...")
    
    # Carregar RAW_LOGS_CACHE
    if os.path.exists(RAW_LOGS_FILE):
        try:
            app.config['RAW_LOGS_CACHE'] = pd.read_pickle(RAW_LOGS_FILE)
            app.logger.info(f"APP: [{datetime.now()}] '{RAW_LOGS_FILE}' carregado com sucesso. {len(app.config['RAW_LOGS_CACHE'])} linhas.")
            
            if 'time_dt' not in app.config['RAW_LOGS_CACHE'].columns or \
               not pd.api.types.is_datetime64_any_dtype(app.config['RAW_LOGS_CACHE']['time_dt']):
                app.logger.info(f"APP: [{datetime.now()}] Coluna 'time_dt' não encontrada ou não é datetime. Tentando criar/converter...")
                if 'time' in app.config['RAW_LOGS_CACHE'].columns:
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['time'], unit='s', errors='coerce')
                elif 'date' in app.config['RAW_LOGS_CACHE'].columns:
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.to_datetime(app.config['RAW_LOGS_CACHE']['date'], errors='coerce')
                else:
                    app.logger.warning(f"APP: [{datetime.now()}] Nenhuma coluna 'time' ou 'date' encontrada para criar 'time_dt' no RAW_LOGS_CACHE.")
                    app.config['RAW_LOGS_CACHE']['time_dt'] = pd.NaT
            
            original_rows = len(app.config['RAW_LOGS_CACHE'])
            app.config['RAW_LOGS_CACHE'].dropna(subset=['time_dt'], inplace=True)
            if len(app.config['RAW_LOGS_CACHE']) < original_rows:
                app.logger.warning(f"APP: [{datetime.now()}] {original_rows - len(app.config['RAW_LOGS_CACHE'])} linhas removidas de RAW_LOGS_CACHE devido a 'time_dt' inválido.")

        except Exception as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro ao carregar ou processar '{RAW_LOGS_FILE}': {e}", exc_info=True)
            app.config['RAW_LOGS_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"APP: [{datetime.now()}] Arquivo '{RAW_LOGS_FILE}' não encontrado. Execute 'collect_raw_logs.py' para coletar logs brutos.")
        app.config['RAW_LOGS_CACHE'] = pd.DataFrame()

    if os.path.exists(PROCESSED_DATA_FILE):
        try:
            app.config['PROCESSED_DATA_CACHE'] = pd.read_csv(PROCESSED_DATA_FILE, encoding='utf-8')
            app.logger.info(f"APP: [{datetime.now()}] '{PROCESSED_DATA_FILE}' carregado com sucesso. {len(app.config['PROCESSED_DATA_CACHE'])} linhas.")
        except Exception as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro ao carregar '{PROCESSED_DATA_FILE}': {e}", exc_info=True)
            app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"APP: [{datetime.now()}] Arquivo '{PROCESSED_DATA_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py'.")
        app.config['PROCESSED_DATA_CACHE'] = pd.DataFrame()

    if os.path.exists(RISK_SCORES_FILE):
        try:
            app.config['RISK_SCORES_CACHE'] = pd.read_csv(RISK_SCORES_FILE, encoding='utf-8')
            app.logger.info(f"APP: [{datetime.now()}] '{RISK_SCORES_FILE}' carregado com sucesso. {len(app.config['RISK_SCORES_CACHE'])} linhas.")
            app.logger.debug(f"APP: Colunas de RISK_SCORES_CACHE: {app.config['RISK_SCORES_CACHE'].columns.tolist()}")
            app.logger.debug(f"APP: Amostra de RISK_SCORES_CACHE:\n{app.config['RISK_SCORES_CACHE'].head().to_string()}")
        except Exception as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro ao carregar '{RISK_SCORES_FILE}': {e}", exc_info=True)
            app.config['RISK_SCORES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"APP: [{datetime.now()}] Arquivo '{RISK_SCORES_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py' ou 'predict_evasion.py'.")
        app.config['RISK_SCORES_CACHE'] = pd.DataFrame()

    if os.path.exists(FEATURES_FILE):
        try:
            app.config['FEATURES_CACHE'] = pd.read_csv(FEATURES_FILE, encoding='utf-8') # Alterado para CSV
            app.logger.info(f"APP: [{datetime.now()}] '{FEATURES_FILE}' carregado com sucesso. {len(app.config['FEATURES_CACHE'])} linhas.")
            app.logger.debug(f"APP: Colunas de FEATURES_CACHE: {app.config['FEATURES_CACHE'].columns.tolist()}")
            app.logger.debug(f"APP: Amostra de FEATURES_CACHE:\n{app.config['FEATURES_CACHE'].head().to_string()}")
        except Exception as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro ao carregar '{FEATURES_FILE}': {e}", exc_info=True)
            app.config['FEATURES_CACHE'] = pd.DataFrame()
    else:
        app.logger.warning(f"APP: [{datetime.now()}] Arquivo '{FEATURES_FILE}' não encontrado. Pode ser necessário executar 'process_evasion_data.py'.")
        app.config['FEATURES_CACHE'] = pd.DataFrame()

    if os.path.exists(PROFESSOR_MAPPING_FILE):
        try:
            with open(PROFESSOR_MAPPING_FILE, 'r', encoding='utf-8') as f:
                app.config['PROFESSOR_COURSE_MAPPING'] = json.load(f)
            app.logger.info(f"APP: [{datetime.now()}] '{PROFESSOR_MAPPING_FILE}' carregado com sucesso. {len(app.config['PROFESSOR_COURSE_MAPPING'])} entradas.")
            app.logger.debug(f"APP: PROFESSOR_COURSE_MAPPING keys: {list(app.config['PROFESSOR_COURSE_MAPPING'].keys())[:5]}")
        except json.JSONDecodeError as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro de decodificação JSON ao carregar '{PROFESSOR_MAPPING_FILE}': {e}", exc_info=True)
            app.config['PROFESSOR_COURSE_MAPPING'] = {}
        except Exception as e:
            app.logger.error(f"APP: [{datetime.now()}] Erro ao carregar '{PROFESSOR_MAPPING_FILE}': {e}", exc_info=True)
            app.config['PROFESSOR_COURSE_MAPPING'] = {}
    else:
        app.logger.warning(f"APP: [{datetime.now()}] Arquivo de mapeamento de professor-curso não encontrado: {PROFESSOR_MAPPING_FILE}. Crie este arquivo para habilitar filtros por professor.")
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
        "professor_course_mapping_loaded": bool(app.config['PROFESSOR_COURSE_MAPPING']),
        "timestamp": datetime.now().isoformat()
    }
    app.logger.info(f"APP: [{datetime.now()}] Health Check: {status}")
    return jsonify(status)

# REGISTRAR BLUEPRINT DE PROFESSOR (COM PREFIXO DE URL)
app.register_blueprint(professor_bp)
app.register_blueprint(evasion_report_bp)
app.register_blueprint(student_bp)
app.register_blueprint(status_bp)
app.register_blueprint(course_bp)
app.register_blueprint(students_overview_bp) # NOVO REGISTRO

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
