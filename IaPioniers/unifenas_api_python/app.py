# app.py
from flask import Flask, jsonify, request, current_app
import pandas as pd
import os
import json
import logging
from datetime import datetime

# Importar Blueprints
from routes.professor_routes import professor_bp
# from routes.student_routes import student_bp # Uncomment if you have student_bp

# Configuração do Logger
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

app = Flask(__name__)

# Definir diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# Criar diretórios se não existirem
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Caminhos dos arquivos
PROCESSED_DATA_FILE = os.path.join(CACHE_DIR, 'processed_evasion_data.csv')
RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')
FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv')
PROFESSOR_MAPPING_FILE = os.path.join(DATA_DIR, 'professor_curso_mapping.json') # NOVO: Caminho para o mapeamento

# Variáveis de cache globais
app.config['PROCESSED_DATA_CACHE'] = None
app.config['RISK_SCORES_CACHE'] = None
app.config['FEATURES_CACHE'] = None
app.config['PROFESSOR_COURSE_MAPPING'] = None # NOVO: Cache para o mapeamento professor-curso

def load_data_to_cache():
    """Carrega os dados processados e de risco de evasão para o cache da aplicação."""
    app.logger.info("Tentando carregar dados para o cache...")
    
    # Carregar df_processed_data
    if os.path.exists(PROCESSED_DATA_FILE):
        try:
            app.config['PROCESSED_DATA_CACHE'] = pd.read_csv(PROCESSED_DATA_FILE, encoding='utf-8') # Adicionado encoding
            app.logger.info(f"'{PROCESSED_DATA_FILE}' carregado com sucesso.")
        except Exception as e:
            app.logger.error(f"Erro ao carregar '{PROCESSED_DATA_FILE}': {e}")
    else:
        app.logger.warning(f"Arquivo '{PROCESSED_DATA_FILE}' não encontrado. Execute 'process_evasion_data.py'.")

    # Carregar df_risk_scores_cache
    if os.path.exists(RISK_SCORES_FILE):
        try:
            # Atenção: Encoding 'utf-8' é crucial aqui, especialmente se o user_name ou course_fullname tiver caracteres especiais
            app.config['RISK_SCORES_CACHE'] = pd.read_csv(RISK_SCORES_FILE, encoding='utf-8')
            app.logger.info(f"'{RISK_SCORES_FILE}' carregado com sucesso.")
            # Verificação de exemplo para 'course_fullname'
            # if 'course_fullname' in app.config['RISK_SCORES_CACHE'].columns:
            #     app.logger.debug(f"Primeiros 5 course_fullname em RISK_SCORES_CACHE: {app.config['RISK_SCORES_CACHE']['course_fullname'].head().tolist()}")
        except Exception as e:
            app.logger.error(f"Erro ao carregar '{RISK_SCORES_FILE}': {e}")
    else:
        app.logger.warning(f"Arquivo '{RISK_SCORES_FILE}' não encontrado. Execute 'evasion_detection.py'.")

    # Carregar df_features_cache
    if os.path.exists(FEATURES_FILE):
        try:
            # Atenção: Encoding 'utf-8' também é crucial aqui
            app.config['FEATURES_CACHE'] = pd.read_csv(FEATURES_FILE, encoding='utf-8')
            app.logger.info(f"'{FEATURES_FILE}' carregado com sucesso.")
            # Verificação de exemplo para 'course_fullname'
            # if 'course_fullname' in app.config['FEATURES_CACHE'].columns:
            #     app.logger.debug(f"Primeiros 5 course_fullname em FEATURES_CACHE: {app.config['FEATURES_CACHE']['course_fullname'].head().tolist()}")
        except Exception as e:
            app.logger.error(f"Erro ao carregar '{FEATURES_FILE}': {e}")
    else:
        app.logger.warning(f"Arquivo '{FEATURES_FILE}' não encontrado. Execute 'process_evasion_data.py'.")

    # Carregar mapeamento professor-curso
    if os.path.exists(PROFESSOR_MAPPING_FILE):
        try:
            # AQUI ESTÁ O PONTO CRÍTICO: Garantir a codificação UTF-8 ao carregar o JSON
            with open(PROFESSOR_MAPPING_FILE, 'r', encoding='utf-8') as f:
                app.config['PROFESSOR_COURSE_MAPPING'] = json.load(f)
            app.logger.info(f"'{PROFESSOR_MAPPING_FILE}' carregado com sucesso.")
            # Verificação de exemplo para o mapeamento
            # app.logger.debug(f"PROFESSOR_COURSE_MAPPING keys: {list(app.config['PROFESSOR_COURSE_MAPPING'].keys())[:5]}")
        except json.JSONDecodeError as e:
            app.logger.error(f"Erro de decodificação JSON ao carregar '{PROFESSOR_MAPPING_FILE}': {e}")
            app.config['PROFESSOR_COURSE_MAPPING'] = {} # Atribui vazio para evitar erros posteriores
        except Exception as e:
            app.logger.error(f"Erro ao carregar '{PROFESSOR_MAPPING_FILE}': {e}")
            app.config['PROFESSOR_COURSE_MAPPING'] = {} # Atribui vazio para evitar erros posteriores
    else:
        app.logger.warning(f"Arquivo de mapeamento de professor-curso não encontrado: {PROFESSOR_MAPPING_FILE}. Crie este arquivo para habilitar filtros por professor.")
        app.config['PROFESSOR_COURSE_MAPPING'] = {} # Definir como dicionário vazio se o arquivo não existir

# Carregar dados quando a aplicação for iniciada
with app.app_context():
    load_data_to_cache()

# Rotas
@app.route('/')
def index():
    return "API de Monitoramento de Evasão UNIFENAS - Acesse /api/professor/course-summaries ou /api/professor-evasion-risk"

@app.route('/health')
def health_check():
    """Verifica o status dos caches de dados."""
    status = {
        "status": "ok",# app.py (Exemplo)
from flask import Flask
# Importe o seu blueprint
from routes.professor_routes import professor_bp
import os
import pandas as pd
import json
import joblib

# Definir diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# Caminhos para os caches que o app.py consome
APP_RISK_SCORES_FILE = os.path.join(CACHE_DIR, 'evasion_predictions_detailed.csv')
APP_FEATURES_FILE = os.path.join(LOCAL_DATA_DIR, 'features_data_for_app.pkl') # Se você salva features separadamente
# Caminho do mapeamento professor-curso
PROFESSOR_COURSE_MAPPING_FILE = os.path.join(LOCAL_DATA_DIR, 'professor_course_mapping.json')


app = Flask(__name__)

# --- Funções para carregar caches (se ainda não as tiver) ---
def load_cached_data():
    df_risk_scores = pd.DataFrame()
    df_features = pd.DataFrame()
    professor_course_mapping = {}

    # Carregar df_risk_scores do CSV gerado por predict_evasion.py
    if os.path.exists(APP_RISK_SCORES_FILE):
        try:
            df_risk_scores = pd.read_csv(APP_RISK_SCORES_FILE)
            # print(f"App: df_risk_scores carregado de {APP_RISK_SCORES_FILE}. Colunas: {df_risk_scores.columns.tolist()}")
            # Adiciona uma verificação para 'evasion_risk' se ainda estiver no código do endpoint
            if 'evasion_risk' not in df_risk_scores.columns and 'is_at_risk' in df_risk_scores.columns:
                print("AVISO: 'evasion_risk' não encontrado em df_risk_scores. Usando 'is_at_risk' para compatibilidade.")
                # df_risk_scores['evasion_risk'] = df_risk_scores['is_at_risk'] # Não é ideal, mas pode ser um fallback
        except Exception as e:
            print(f"Erro ao carregar df_risk_scores do CSV: {e}")
            df_risk_scores = pd.DataFrame()
    else:
        print(f"AVISO: {APP_RISK_SCORES_FILE} não encontrado. Dados de risco de evasão não disponíveis.")

    # Carregar df_features. Este precisa ser o DataFrame completo que gerou as features
    # Se 'predict_evasion.py' não salva as features em um arquivo separado para o app consumir,
    # você precisará ajustar isso. O df_features_cache é o df_features_for_prediction
    # gerado por process_moodle_logs_for_evasion.
    # Por simplicidade, vamos assumir que predict_evasion salva isso também ou que você
    # recalcule aqui (não recomendado)
    # Por enquanto, se não for salvo, essa parte pode estar vazia ou precisar de outra fonte.
    # Para testar, você pode comentar df_features_cache ou certificar-se que ele é carregado
    # Ou, como um hack TEMPORÁRIO para fazer o endpoint funcionar,
    # você pode carregar o df_raw_logs_for_prediction e processá-lo aqui
    # (mas isso é caro, apenas para testar o endpoint rapidamente)

# Carregar df_features
    if os.path.exists(APP_FEATURES_FILE):
        try:
            df_features = pd.read_pickle(APP_FEATURES_FILE) # Use pd.read_csv se salvou como CSV
            print(f"App: df_features carregado de {APP_FEATURES_FILE}.")
        except Exception as e:
            print(f"Erro ao carregar df_features: {e}")
            df_features = pd.DataFrame()
    else:
        print(f"AVISO: {APP_FEATURES_FILE} não encontrado. Dados de features não disponíveis para o app.")

    # Carregar mapeamento professor-curso
    if os.path.exists(PROFESSOR_COURSE_MAPPING_FILE):
        try:
            with open(PROFESSOR_COURSE_MAPPING_FILE, 'r', encoding='utf-8') as f:
                professor_course_mapping = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar professor_course_mapping.json: {e}")
    else:
        print(f"AVISO: {PROFESSOR_COURSE_MAPPING_FILE} não encontrado.")

    return df_risk_scores, df_features, professor_course_mapping

# Carrega os caches na inicialização do app
df_risk_scores_cache, df_features_cache, professor_course_mapping_cache = load_cached_data()

# Armazenar os DataFrames e o mapeamento na configuração do aplicativo
app.config['RISK_SCORES_CACHE'] = df_risk_scores_cache
app.config['FEATURES_CACHE'] = df_features_cache # Certifique-se que este cache é preenchido!
app.config['PROFESSOR_COURSE_MAPPING'] = professor_course_mapping_cache

# REGISTRAR O BLUEPRINT AQUI!
app.register_blueprint(professor_bp) # <-- ESTA É A LINHA CRÍTICA QUE FALTARIA

if __name__ == '__main__':
    app.run(debug=True) # ou host='0.0.0.0' para acesso externo
        "processed_data_loaded": app.config['PROCESSED_DATA_CACHE'] is not None and not app.config['PROCESSED_DATA_CACHE'].empty,
        "risk_scores_loaded": app.config['RISK_SCORES_CACHE'] is not None and not app.config['RISK_SCORES_CACHE'].empty,
        "features_loaded": app.config['FEATURES_CACHE'] is not None and not app.config['FEATURES_CACHE'].empty,
        "professor_course_mapping_loaded": app.config['PROFESSOR_COURSE_MAPPING'] is not None and bool(app.config['PROFESSOR_COURSE_MAPPING']),
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(status)

# Registrar Blueprints
app.register_blueprint(professor_bp, url_prefix='/api')
# app.register_blueprint(student_bp, url_prefix='/api') # Uncomment if you have student_bp

if __name__ == '__main__':
    # No ambiente de produção, use um servidor WSGI como Gunicorn ou uWSGI
    # Este é um servidor de desenvolvimento, não recomendado para produção
    app.run(debug=True)