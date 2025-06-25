# process_evasion_data.py
import pandas as pd
from datetime import datetime, timedelta
import joblib # Para salvar/carregar o modelo
import json # Para salvar/carregar a lista de features
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve, auc
import numpy as np

# Definir diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, 'local_data') # Para arquivos internos do pipeline (modelo, features do modelo, cache interno de logs)
CACHE_DIR = os.path.join(BASE_DIR, 'cache') # Para arquivos que a API (app.py) consome

# Criar diretórios se não existirem
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


# Definição do caminho do cache e do modelo (apenas para uso interno deste script)
RAW_LOGS_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, 'raw_logs_cache.pkl')
MODEL_FILENAME = 'evasion_model.joblib'
FEATURES_FILENAME = 'model_features.json'

# Caminhos corretos para salvar/carregar em local_data
MODEL_PATH = os.path.join(LOCAL_DATA_DIR, MODEL_FILENAME)
FEATURES_PATH = os.path.join(LOCAL_DATA_DIR, FEATURES_FILENAME)

# Caminhos para os arquivos que o app.py espera, salvos no CACHE_DIR
APP_PROCESSED_DATA_FILE = os.path.join(CACHE_DIR, 'processed_evasion_data.csv')
APP_FEATURES_FILE = os.path.join(CACHE_DIR, 'student_features.csv')


# Definição do limiar de inatividade para evasão
INACTIVITY_THRESHOLD_DAYS = 30 # Aluno é considerado evadido se não acessa há mais de X dias

def process_moodle_logs_for_evasion(df_raw_logs: pd.DataFrame, inactivity_threshold_days: int = INACTIVITY_THRESHOLD_DAYS):
    """
    Processa os logs brutos do Moodle para extrair features relevantes para previsão de evasão.
    Inclui agora mais features para o calculador de risco baseado em regras.
    
    Args:
        df_raw_logs (pd.DataFrame): DataFrame contendo os logs brutos do Moodle.
                                    Deve incluir 'user_id', 'course_fullname', 'date' (datetime),
                                    'user_lastaccess' (datetime ou timestamp), 'eventname', 'action', 'component'.
        inactivity_threshold_days (int): Número de dias de inatividade para considerar um aluno evadido.
                                         Este é o 'Y' na regra "não acessa há mais de Y dias".
                                        
    Returns:
        pd.DataFrame: DataFrame com features prontas para o modelo e para as regras, incluindo 'is_evaded'.
    """
    if df_raw_logs.empty:
        print(f"[{datetime.now()}] DataFrame de logs brutos vazio. Retornando DataFrame de features vazio.")
        return pd.DataFrame()

    print(f"[{datetime.now()}] Iniciando processamento de features para evasão...")

    # Garante que as colunas essenciais existem e trata as ausentes
    required_cols_for_processing = ['user_id', 'user_name', 'course_fullname', 'date', 'user_lastaccess', 'eventname', 'action', 'component', 'target']
    
    for col in required_cols_for_processing:
        if col not in df_raw_logs.columns:
            if col == 'course_fullname':
                df_raw_logs['course_fullname'] = 'Curso Desconhecido'
            elif col == 'user_name':
                df_raw_logs['user_name'] = df_raw_logs['user_id'].astype(str) # Usa user_id como fallback para user_name
            elif col in ['eventname', 'action', 'component', 'target']:
                df_raw_logs[col] = '' # Preenche com string vazia para eventos/ações/componentes/targets ausentes
            else:
                print(f"[{datetime.now()}] Erro: Coluna '{col}' essencial não encontrada no DataFrame de logs brutos. Abortando processamento.")
                return pd.DataFrame()

    # Conversão para datetime
    df_raw_logs['date'] = pd.to_datetime(df_raw_logs['date'], errors='coerce')
    if pd.api.types.is_numeric_dtype(df_raw_logs['user_lastaccess']):
        df_raw_logs['user_lastaccess'] = pd.to_datetime(df_raw_logs['user_lastaccess'], unit='s', errors='coerce')
    else:
        df_raw_logs['user_lastaccess'] = pd.to_datetime(df_raw_logs['user_lastaccess'], errors='coerce')
        
    # Remover linhas com datas inválidas após a conversão
    df_raw_logs.dropna(subset=['date', 'user_lastaccess'], inplace=True)
    if df_raw_logs.empty:
        print(f"[{datetime.now()}] DataFrame vazio após remoção de datas inválidas.")
        return pd.DataFrame()

    # Garantir tipos de dados corretos para IDs e texto
    df_raw_logs['user_id'] = df_raw_logs['user_id'].astype(str)
    df_raw_logs['user_name'] = df_raw_logs['user_name'].astype(str)
    df_raw_logs['course_fullname'] = df_raw_logs['course_fullname'].astype(str)
    df_raw_logs['eventname'] = df_raw_logs['eventname'].astype(str).str.lower()
    df_raw_logs['action'] = df_raw_logs['action'].astype(str).str.lower()
    df_raw_logs['component'] = df_raw_logs['component'].astype(str).str.lower()
    df_raw_logs['target'] = df_raw_logs['target'].astype(str).str.lower()


    # Calcular a data de referência como a data mais recente nos logs
    current_date = df_raw_logs['date'].max()

    # --- FEATURES GLOBAIS POR USUÁRIO ---
    # Inatividade Global (já existe como 'overall_last_access_days_ago' no df_features final)
    latest_user_access = df_raw_logs.groupby('user_id')['user_lastaccess'].max().reset_index()
    latest_user_access.rename(columns={'user_lastaccess': 'actual_user_last_access_date'}, inplace=True)
    latest_user_access['overall_last_access_days_ago'] = (current_date - latest_user_access['actual_user_last_access_date']).dt.days

    # Total de Ações Globais por Usuário
    total_actions_global = df_raw_logs.groupby('user_id').size().reset_index(name='total_actions_global')

    # Contagem de Posts em Fóruns Globais por Usuário
    forum_posts = df_raw_logs[
        (df_raw_logs['component'] == 'mod_forum') | (df_raw_logs['component'] == 'mod_discussion') |
        (df_raw_logs['action'].str.contains('posted|replied|created'))
    ].groupby('user_id').size().reset_index(name='global_forum_posts_count')

    # Contagem de Tentativas de Quiz Globais por Usuário
    quiz_attempts = df_raw_logs[
        (df_raw_logs['component'] == 'mod_quiz') &
        (df_raw_logs['action'].str.contains('attempt|started|submitted'))
    ].groupby('user_id').size().reset_index(name='global_quiz_attempts_count')

    # --- FEATURES POR USUÁRIO E CURSO ---
    df_course_user_agg = df_raw_logs.groupby(['user_id', 'user_name', 'course_fullname']).agg(
        course_activity_count=('date', 'count'), # Número total de atividades no curso
        course_unique_actions=('action', lambda x: x.nunique()), # Quantidade de ações únicas
        course_last_activity_date=('date', 'max'), # Última atividade específica do curso
        course_first_activity_date=('date', 'min') # Primeira atividade específica do curso
    ).reset_index()

    # Calcular dias desde a última atividade no curso
    df_course_user_agg['course_last_activity_days_ago'] = (current_date - df_course_user_agg['course_last_activity_date']).dt.days

    # Calcular a duração da atividade do aluno no curso (do primeiro ao último log conhecido)
    df_course_user_agg['course_activity_duration_days'] = (df_course_user_agg['course_last_activity_date'] - df_course_user_agg['course_first_activity_date']).dt.days
    # REMOVIDA A LINHA ABAIXO QUE CAUSAVA O ERRO:
    # df_course_user_agg['course_activity_duration_days'] = df_course_user_agg['course_activity_duration_days'].dt.days # Converter para int

    # Calcular 'engagement_per_day' (atividades por dia de duração no curso)
    df_course_user_agg['engagement_per_day'] = df_course_user_agg['course_activity_count'] / (df_course_user_agg['course_activity_duration_days'].replace(0, 1) + 1)
    
    # Número de tipos únicos de recurso acessados por curso
    resource_access_types = df_raw_logs[
        (df_raw_logs['action'].str.contains('viewed|accessed')) & 
        (df_raw_logs['component'].str.contains('mod_resource|mod_page|mod_url|mod_folder|mod_book|mod_lesson|mod_file|mod_glossary'))
    ].groupby(['user_id', 'course_fullname'])['component'].nunique().reset_index(name='unique_resource_types_accessed_course')


    # --- MERGE DE TODAS AS FEATURES EM UM ÚNICO DATAFRAME ---
    df_features = df_course_user_agg.copy()

    # Merge com as features globais
    df_features = pd.merge(df_features, latest_user_access[['user_id', 'overall_last_access_days_ago', 'actual_user_last_access_date']], on='user_id', how='left')
    df_features = pd.merge(df_features, total_actions_global, on='user_id', how='left')
    df_features = pd.merge(df_features, forum_posts, on='user_id', how='left')
    df_features = pd.merge(df_features, quiz_attempts, on='user_id', how='left')
    df_features = pd.merge(df_features, resource_access_types, on=['user_id', 'course_fullname'], how='left')

    # --- FEATURES MAIS COMPLEXAS (LÓGICA SIMPLIFICADA OU DEFAULT) ---
    # A implementação completa dessas features exige mais dados e lógica de negócios (ciclos acadêmicos, etc.)
    # Para fins de teste e demonstração, vamos dar valores padrão ou lógicas muito simplificadas.

    # is_in_first_activity_cycle_no_submission (Exemplo simplificado: nenhum submission no curso nos primeiros 7 dias)
    # Requer que você tenha uma forma de identificar a "primeira atividade" ou "ciclo"
    # Placeholder: assume False por padrão ou True para alunos com 0 atividades nos primeiros dias do curso.
    # Esta feature é difícil de calcular sem um contexto de "ciclo" e "atividades de submissão"
    # Vamos defini-la como False por padrão, e você pode refinar.
    df_features['is_in_first_activity_cycle_no_submission'] = False
    # Exemplo de lógica simplificada para fins de teste/demo (requer df_raw_logs com eventnames de submissão):
    # alunos_sem_submissao_primeiros_dias = df_raw_logs[
    #     (df_raw_logs['date'] - df_raw_logs.groupby('user_id')['date'].transform('min')).dt.days <= 7
    # ].groupby('user_id').apply(lambda x: not x['action'].str.contains('submitted|graded').any())
    # df_features['is_in_first_activity_cycle_no_submission'] = df_features['user_id'].isin(alunos_sem_submissao_primeiros_dias[alunos_sem_submissao_primeiros_dias].index)


    # has_recent_visual_interaction_in_cycle (Ligado à feature acima)
    # Placeholder: True por padrão, a menos que você tenha uma forma de identificar.
    df_features['has_recent_visual_interaction_in_cycle'] = True 
    # Exemplo de lógica simplificada (requer df_raw_logs com actions de visualização):
    # visual_interaction_types = ['viewed', 'accessed']
    # has_visual_interaction = df_raw_logs[
    #     df_raw_logs['action'].isin(visual_interaction_types)
    # ].groupby('user_id').size() > 0
    # df_features['has_recent_visual_interaction_in_cycle'] = df_features['user_id'].map(has_visual_interaction).fillna(False)


    # has_falling_trend_90_days (Muito complexo, requer série temporal de logs)
    # Placeholder: False por padrão.
    df_features['has_falling_trend_90_days'] = False
    # Exemplo (muito simplificado, não recomendado para produção sem mais dados):
    # if 'daily_activity_count' in df_raw_logs.columns: # Você precisaria gerar isso primeiro
    #     df_features['has_falling_trend_90_days'] = df_raw_logs.groupby('user_id')['daily_activity_count'].apply(
    #         lambda x: len(x) >= 90 and x.tail(30).mean() < x.head(30).mean() # Média dos últimos 30 dias < primeiros 30
    #     ).fillna(False)


    # --- Lidar com NaNs que possam surgir de merges ou cálculos ---
    # Preencher NaNs em colunas numéricas com 0 (ou um valor mais apropriado)
    numeric_cols_for_fillna = [
        'overall_last_access_days_ago', 'total_actions_global', 
        'global_forum_posts_count', 'global_quiz_attempts_count',
        'unique_resource_types_accessed_course', 
        'course_activity_count', 'course_unique_actions',
        'course_last_activity_days_ago', 'course_activity_duration_days',
        'engagement_per_day'
    ]
    for col in numeric_cols_for_fillna:
        if col in df_features.columns:
            df_features[col] = df_features[col].fillna(0)
    
    # Preencher NaNs em colunas booleanas com False
    boolean_cols_for_fillna = [
        'is_in_first_activity_cycle_no_submission',
        'has_recent_visual_interaction_in_cycle',
        'has_falling_trend_90_days'
    ]
    for col in boolean_cols_for_fillna:
        if col in df_features.columns:
            df_features[col] = df_features[col].fillna(False)


    # Criar a variável alvo: is_evaded
    # Um aluno é considerado "evadido" se o seu 'overall_last_access_days_ago' (ultimo acesso geral no Moodle)
    # ou 'course_last_activity_days_ago' (ultimo acesso especifico do curso)
    # exceder o limiar de inatividade.
    df_features['is_evaded'] = ((df_features['overall_last_access_days_ago'] > inactivity_threshold_days) |
                                 (df_features['course_last_activity_days_ago'] > inactivity_threshold_days)).astype(int)

    print(f"[{datetime.now()}] Processamento de features concluído.")
    print(f"[{datetime.now()}] Total de entradas de features (alunos x cursos): {len(df_features)}")
    print(f"[{datetime.now()}] Amostra de features geradas:\n{df_features.head()}")
    
    return df_features

def train_and_save_model(df_features: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
    """
    Treina um modelo de classificação e o salva junto com a lista de features usadas.
    
    Args:
        df_features (pd.DataFrame): DataFrame com as features e a variável alvo 'is_evaded'.
        test_size (float): Proporção dos dados a serem usados para teste.
        random_state (int): Semente para reprodutibilidade.
        
    Returns:
        tuple: (model, feature_names) se o treinamento for bem-sucedido, None caso contrário.
    """
    if df_features.empty:
        print(f"[{datetime.now()}] DataFrame de features vazio. Não é possível treinar o modelo.")
        return None, None

    # As features para o modelo (colunas numéricas, exceto as de identificação e a variável alvo)
    # Exclua colunas que não são features numéricas para o modelo
    features_to_exclude = [
        'user_id', 'user_name', 'course_fullname', 'is_evaded', 
        'course_last_activity_date', 'course_first_activity_date',
        'actual_user_last_access_date'
    ]
    
    # Selecionar apenas colunas numéricas que não estão na lista de exclusão
    X = df_features.select_dtypes(include=[np.number]).drop(columns=[col for col in features_to_exclude if col in df_features.columns and col in df_features.select_dtypes(include=[np.number]).columns], errors='ignore')
    
    # Adicionar colunas booleanas que podem ser usadas como features no modelo
    # Converte booleans para inteiros (True=1, False=0)
    boolean_features_for_model = [
        'is_in_first_activity_cycle_no_submission',
        'has_recent_visual_interaction_in_cycle',
        'has_falling_trend_90_days'
    ]
    for b_col in boolean_features_for_model:
        if b_col in df_features.columns and b_col not in X.columns:
            X[b_col] = df_features[b_col].astype(int)


    y = df_features['is_evaded']

    # Lidar com NaNs, por exemplo, preenchendo com 0.
    X = X.fillna(0) 

    # Verifique se ainda há features para o treinamento após a exclusão
    if X.empty or X.shape[1] == 0:
        print(f"[{datetime.now()}] Nenhuma feature numérica ou booleana válida encontrada após o pré-processamento para treinamento. Abortando.")
        return None, None
    
    # Lista das features que o modelo usará - essencial para garantir consistência na predição
    model_features = X.columns.tolist()

    print(f"[{datetime.now()}] Features selecionadas para treinamento: {model_features}")
    print(f"[{datetime.now()}] Balanceamento da classe 'is_evaded':\n{y.value_counts(normalize=True)}")

    # Dividir dados em treino e teste
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
    except ValueError as e:
        print(f"[{datetime.now()}] Erro ao dividir os dados (provavelmente classe única no 'y'): {e}")
        print(f"[{datetime.now()}] Classes em 'is_evaded': {y.unique()}")
        if len(y.unique()) < 2:
            print(f"[{datetime.now()}] A variável alvo 'is_evaded' contém apenas uma classe. Não é possível treinar um classificador.")
            return None, None
        
    print(f"[{datetime.now()}] Tamanho do conjunto de treino: {len(X_train)} amostras.")
    print(f"[{datetime.now()}] Tamanho do conjunto de teste: {len(X_test)} amostras.")

    # Treinar o modelo (RandomForestClassifier como exemplo)
    print(f"[{datetime.now()}] Treinando o modelo RandomForestClassifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=random_state, class_weight='balanced') # 'balanced' para lidar com desequilíbrio de classes
    model.fit(X_train, y_train)
    print(f"[{datetime.now()}] Modelo treinado com sucesso.")

    # Avaliar o modelo
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] # Probabilidade da classe positiva (evadido)

    print(f"\n[{datetime.now()}] Relatório de Classificação no conjunto de teste:\n{classification_report(y_test, y_pred)}")
    print(f"[{datetime.now()}] AUC-ROC: {roc_auc_score(y_test, y_prob):.4f}")

    # Curva Precision-Recall (P-R curve) é frequentemente mais informativa para classes desbalanceadas
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    auc_pr = auc(recall, precision)
    print(f"[{datetime.now()}] AUC-PR: {auc_pr:.4f}")

    # Salvar o modelo treinado
    joblib.dump(model, MODEL_PATH)
    print(f"[{datetime.now()}] Modelo salvo em: {MODEL_PATH}")

    # Salvar a lista de features usadas pelo modelo
    with open(FEATURES_PATH, 'w') as f:
        json.dump(model_features, f)
    print(f"[{datetime.now()}] Lista de features salva em: {FEATURES_PATH}")

    return model, model_features

def run_training_pipeline():
    """
    Função principal para executar o pipeline de treinamento do modelo usando dados do cache.
    """
    print(f"\n--- [{datetime.now()}] Iniciando Pipeline de Treinamento do Modelo ---")

    # 1. Carregar o DataFrame de logs brutos completo do cache
    df_raw_logs_historical = pd.DataFrame()
    if os.path.exists(RAW_LOGS_CACHE_FILE):
        try:
            df_raw_logs_historical = pd.read_pickle(RAW_LOGS_CACHE_FILE)
            print(f"[{datetime.now()}] {len(df_raw_logs_historical)} logs históricos carregados do cache para processamento.")
            
            # Garante que 'date' e 'user_lastaccess' são datetime, e que 'user_id' e 'course_fullname' são strings
            df_raw_logs_historical['date'] = pd.to_datetime(df_raw_logs_historical['date'], errors='coerce')
            
            # Lidar com user_lastaccess que pode vir como timestamp ou string
            if pd.api.types.is_string_dtype(df_raw_logs_historical['user_lastaccess']):
                df_raw_logs_historical['user_lastaccess'] = pd.to_datetime(df_raw_logs_historical['user_lastaccess'], errors='coerce')
            elif pd.api.types.is_numeric_dtype(df_raw_logs_historical['user_lastaccess']):
                df_raw_logs_historical['user_lastaccess'] = pd.to_datetime(df_raw_logs_historical['user_lastaccess'], unit='s', errors='coerce')

            df_raw_logs_historical['user_id'] = df_raw_logs_historical['user_id'].astype(str)
            if 'course_fullname' not in df_raw_logs_historical.columns:
                df_raw_logs_historical['course_fullname'] = 'Curso Desconhecido'
            else:
                df_raw_logs_historical['course_fullname'] = df_raw_logs_historical['course_fullname'].astype(str)
            
            # Remover linhas onde as colunas essenciais são NaN após conversão
            df_raw_logs_historical.dropna(subset=['date', 'user_lastaccess', 'user_id'], inplace=True)

        except Exception as e:
            print(f"[{datetime.now()}] Erro ao carregar ou processar cache histórico para treinamento: {e}")
            df_raw_logs_historical = pd.DataFrame() # Reseta para DataFrame vazio se houver erro
    else:
        print(f"[{datetime.now()}] Cache de logs brutos '{RAW_LOGS_CACHE_FILE}' não encontrado. Não é possível treinar o modelo sem dados. Por favor, execute 'collect_raw_logs.py' primeiro.")
        return

    if df_raw_logs_historical.empty:
        print(f"[{datetime.now()}] Nenhum log histórico válido para treinar o modelo. Abortando treinamento.")
        return
        
    # Salvar o df_raw_logs_historical (processado) como 'processed_evasion_data.csv' para o app.py
    try:
        df_raw_logs_historical.to_csv(APP_PROCESSED_DATA_FILE, index=False, encoding='utf-8')
        print(f"[{datetime.now()}] Dados brutos processados salvos para o app.py em: {APP_PROCESSED_DATA_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Erro ao salvar '{APP_PROCESSED_DATA_FILE}': {e}")


    # 2. Processar os logs brutos para extrair features
    df_features = process_moodle_logs_for_evasion(df_raw_logs_historical, inactivity_threshold_days=INACTIVITY_THRESHOLD_DAYS)

    if df_features.empty:
        print(f"[{datetime.now()}] Nenhum feature processada para treinamento. DataFrame de features vazio.")
        return

    # NOVO: Salvar o df_features gerado como 'student_features.csv' para o app.py
    try:
        df_features.to_csv(APP_FEATURES_FILE, index=False, encoding='utf-8')
        print(f"[{datetime.now()}] Features processadas (student_features.csv) salvas para o app.py em: {APP_FEATURES_FILE}")
    except Exception as e:
        print(f"[{datetime.now()}] Erro ao salvar '{APP_FEATURES_FILE}': {e}")


    # 3. Treinar e salvar o modelo (no LOCAL_DATA_DIR, como antes)
    model, features = train_and_save_model(df_features)

    if model and features:
        print(f"\n--- [{datetime.now()}] Pipeline de Treinamento do Modelo Concluído com Sucesso ---")
    else:
        print(f"\n--- [{datetime.now()}] Pipeline de Treinamento do Modelo Falhou ---")

# Bloco de execução principal para process_evasion_data.py
if __name__ == '__main__':
    run_training_pipeline()
