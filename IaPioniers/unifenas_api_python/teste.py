import pandas as pd
import os

FEATURES_CACHE_PATH = os.path.join(os.path.dirname(__file__), 'local_data', 'features_only_cache.pkl')

if os.path.exists(FEATURES_CACHE_PATH):
    df_features = pd.read_pickle(FEATURES_CACHE_PATH)
    print("Valores únicos de 'course_id':")
    print(df_features['course_id'].unique())
    print("\nValores únicos de 'course_fullname':")
    print(df_features['course_fullname'].unique())
else:
    print("features_only_cache.pkl não encontrado. Execute process_evasion_data.py.")