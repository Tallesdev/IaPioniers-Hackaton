# moodle_api_config.py
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp

# --- Configurações da API Moodle ---
MOODLE_API_BASE_URL = "https://api.unifenas.br/v1"
UNIFENAS_EMAIL = "hackathon@unifenas.br"
UNIFENAS_PASSWORD = "hackathon#2025"

# --- Configuração de Delay e Concorrência ---
REQUEST_DELAY_SECONDS = 0.5 # Ajustando para 0.5s para maior chance de sucesso inicial
MAX_CONCURRENT_REQUESTS = 5 # Mantenha em 5 por enquanto.

# --- Configurações de Retry ---
RETRY_SETTINGS = {
    'stop': stop_after_attempt(5),
    'wait': wait_exponential(multiplier=1, min=2, max=60),
    'retry': retry_if_exception_type(aiohttp.ClientError),
    'reraise': True
}