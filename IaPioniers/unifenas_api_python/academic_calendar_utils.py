# academic_calendar_utils.py
from datetime import date, datetime, timedelta

# --- Definições de Recessos Fixos (apenas mês/dia - o ano é um placeholder '1') ---
RECESS_START_DEC = date(1, 12, 20) # 20 de Dezembro
RECESS_END_MAR = date(1, 3, 11)    # 11 de Março
RECESS_START_JUL = date(1, 7, 1)   # 1 de Julho
RECESS_END_JUL = date(1, 7, 31)    # 31 de Julho

# Limite de inatividade (mantido como está)
THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS = 3

# --- NOVAS DEFINIÇÕES DE MÓDULOS FIXOS POR ANO ---
# Este dicionário define os períodos dos módulos por ano de forma explícita.
_FIXED_MODULE_BOUNDARIES = {
    2025: [
        {"module_number": 1, "start_date": date(2025, 3, 11), "end_date": date(2025, 5, 4)},
        {"module_number": 2, "start_date": date(2025, 5, 5), "end_date": date(2025, 6, 28)}, # <-- OK, termina em 28 de junho!
        {"module_number": 3, "start_date": date(2025, 8, 1), "end_date": date(2025, 9, 27)},
        {"module_number": 4, "start_date": date(2025, 9, 28), "end_date": date(2025, 11, 24)},
    ]
}


# --- Funções Auxiliares Internas (usadas para o cálculo inicial do calendário) ---
# Estas funções usam apenas as regras de recesso BÁSICAS para evitar circularidade
# durante o cálculo dos domingos especiais.

def _is_basic_recess(check_date: date) -> bool:
    """
    Verifica se uma dada data é um recesso básico (fixos anuais + 10 de Março).
    IMPORTANTE: NÃO considera sábados/domingos ou os 5 primeiros domingos dinâmicos.
    """
    # Recesso específico do dia 10 de Março (para o ano da data sendo verificada)
    if check_date == date(check_date.year, 3, 10):
        return True

    # Recesso de Julho (ignora o ano, apenas mês/dia)
    if RECESS_START_JUL.month <= check_date.month <= RECESS_END_JUL.month:
        if (check_date.month == RECESS_START_JUL.month and check_date.day >= RECESS_START_JUL.day) or \
           (check_date.month == RECESS_END_JUL.month and check_date.day <= RECESS_END_JUL.day) or \
           (RECESS_START_JUL.month < check_date.month < RECESS_END_JUL.month):
            return True

    # Recesso de Dezembro a Março (ignora o ano, apenas mês/dia - lida com virada do ano)
    if (check_date.month == RECESS_START_DEC.month and check_date.day >= RECESS_START_DEC.day) or \
       (check_date.month >= 1 and check_date.month < RECESS_END_MAR.month) or \
       (check_date.month == RECESS_END_MAR.month and check_date.day <= RECESS_END_MAR.day):
        return True
            
    return False

def _get_academic_date_after_basic(start_date: date, num_days: int) -> date:
    """
    Calcula uma data que está 'num_days' dias acadêmicos BÁSICOS depois de 'start_date'.
    Usa _is_basic_recess.
    """
    current_date = start_date
    days_counted = 0
    safety_counter = 0
    max_safety_days = 365 * 2 # Limite de segurança para evitar loops infinitos
    while days_counted < num_days:
        current_date += timedelta(days=1) # Avança um dia calendário
        if not _is_basic_recess(current_date): # Verifica se é um dia acadêmico básico
            days_counted += 1
        safety_counter += 1
        if safety_counter > max_safety_days:
            raise ValueError(f"Não foi possível encontrar a data acadêmica básica {num_days} dias depois de {start_date}.")
    return current_date

# --- Cálculo Dinâmico de Datas Não-Acadêmicas para o Ano ---
_calculated_all_non_academic_dates_cache = {} # Cache para armazenar o resultado por ano

def _calculate_all_non_academic_dates_for_year(year: int) -> set:
    """
    Calcula e retorna um conjunto de TODAS as datas não acadêmicas para um dado ano.
    Isso inclui recessos fixos, datas específicas (como 10/03) e os 5 primeiros domingos
    do primeiro e terceiro módulos, com base nos *módulos fixos*.
    """
    if year in _calculated_all_non_academic_dates_cache:
        return _calculated_all_non_academic_dates_cache[year]

    all_non_academic_dates = {date(year, 3, 10)} # Começa com a data de recesso específica 10/03

    # Verifica se os módulos fixos estão definidos para o ano e se há módulos suficientes
    if year not in _FIXED_MODULE_BOUNDARIES or len(_FIXED_MODULE_BOUNDARIES[year]) < 3:
        # Se não houver módulos fixos definidos ou menos de 3 módulos (para M1 e M3),
        # apenas retorna os recessos básicos e a data 10/03.
        print(f"Aviso: Módulos fixos para o ano {year} não totalmente definidos ou insuficientes para calcular domingos especiais (requer pelo menos 3 módulos).")
        _calculated_all_non_academic_dates_cache[year] = all_non_academic_dates
        return all_non_academic_dates

    modules_for_year = _FIXED_MODULE_BOUNDARIES[year]
    
    # --- Identifica os 5 Primeiros Domingos para o PRIMEIRO MÓDULO (baseado em sua data fixa de início) ---
    # Encontra o primeiro dia acadêmico REAL do Módulo 1 fixo
    first_module_fixed_start = modules_for_year[0]["start_date"]
    first_academic_day_of_module_1 = first_module_fixed_start
    while _is_basic_recess(first_academic_day_of_module_1):
        first_academic_day_of_module_1 += timedelta(days=1)

    # Define o período para buscar os 5 domingos como o próprio período do módulo fixo.
    end_date_for_sunday_search_m1 = modules_for_year[0]["end_date"]
    
    sunday_count = 0
    temp_date_iter = first_academic_day_of_module_1
    while sunday_count < 5 and temp_date_iter <= end_date_for_sunday_search_m1:
        if temp_date_iter.weekday() == 6: # Se for domingo (weekday() retorna 6 para domingo)
            all_non_academic_dates.add(temp_date_iter) # Adiciona este domingo como não-acadêmico
            sunday_count += 1
        temp_date_iter += timedelta(days=1)

    # --- Identifica os 5 Primeiros Domingos para o TERCEIRO MÓDULO (baseado em sua data fixa de início) ---
    # Encontra o primeiro dia acadêmico REAL do Módulo 3 fixo
    third_module_fixed_start = modules_for_year[2]["start_date"] # Módulo 3 é o índice 2 na lista
    first_academic_day_of_module_3 = third_module_fixed_start
    while _is_basic_recess(first_academic_day_of_module_3):
        first_academic_day_of_module_3 += timedelta(days=1)
    
    end_date_for_sunday_search_m3 = modules_for_year[2]["end_date"]

    sunday_count = 0
    temp_date_iter = first_academic_day_of_module_3
    while sunday_count < 5 and temp_date_iter <= end_date_for_sunday_search_m3:
        if temp_date_iter.weekday() == 6: # Se for domingo
            all_non_academic_dates.add(temp_date_iter) # Adiciona este domingo como não-acadêmico
            sunday_count += 1
        temp_date_iter += timedelta(days=1)
            
    _calculated_all_non_academic_dates_cache[year] = all_non_academic_dates
    return all_non_academic_dates

# --- Conjunto Global de Todas as Datas Não-Acadêmicas para o Ano ---
# Este conjunto será populado quando o módulo `academic_calendar_utils` for importado.
# Ele conterá todas as datas que `is_academic_recess` considerará não-acadêmicas.
_current_year_for_init = date.today().year

# Realiza o cálculo e preenche o conjunto global na importação do módulo
# A função _calculate_all_non_academic_dates_for_year agora usa _FIXED_MODULE_BOUNDARIES internamente
ALL_NON_ACADEMIC_DATES_FOR_YEAR = _calculate_all_non_academic_dates_for_year(_current_year_for_init)

# --- Função Pública `is_academic_recess` ---
# Esta é a função que o resto da sua aplicação deve chamar.
def is_academic_recess(check_date: date) -> bool:
    """
    Verifica se uma dada data é considerada recesso acadêmico (público).
    A decisão é baseada no conjunto pré-calculado de todas as datas não-acadêmicas para o ano.
    """
    # Apenas verifica se a data está no conjunto pré-calculado
    return check_date in ALL_NON_ACADEMIC_DATES_FOR_YEAR

# --- Funções Públicas de Navegação de Dias Acadêmicos (usam a is_academic_recess completa) ---
# Essas são as funções que você já tinha ou que foram adicionadas anteriormente.
# Agora elas usarão o novo `is_academic_recess` que considera todas as suas regras.

def calculate_academic_days_between(start_date: date, end_date: date) -> int:
    """
    Calcula o número de dias acadêmicos entre duas datas, excluindo recessos.
    """
    count = 0
    current_date = start_date
    while current_date <= end_date:
        if not is_academic_recess(current_date): # Usa a is_academic_recess pública
            count += 1
        current_date += timedelta(days=1)
    return count

def calculate_academic_days_since(target_date: date) -> int:
    """
    Calcula o número de dias acadêmicos desde uma data alvo até hoje, excluindo recessos.
    """
    today = date.today()
    if target_date > today:
        return 0
    return calculate_academic_days_between(target_date, today) # Usa a is_academic_recess pública

def get_academic_date_ago(start_date: date, num_days: int) -> date:
    """
    Calcula uma data que está 'num_days' dias acadêmicos antes de 'start_date'.
    Usa a função is_academic_recess completa.
    """
    current_date = start_date
    days_counted = 0
    target_academic_days_to_find = num_days + 1
    safety_counter = 0
    max_safety_days = 365 * 2

    while days_counted < target_academic_days_to_find:
        if not is_academic_recess(current_date): # Usa a is_academic_recess pública
            days_counted += 1
            
        if days_counted == target_academic_days_to_find:
            return current_date
            
        current_date -= timedelta(days=1)
        safety_counter += 1
        if safety_counter > max_safety_days:
            raise ValueError(f"Não foi possível encontrar a data acadêmica {num_days} dias antes de {start_date} dentro de {max_safety_days} dias calendário. Verifique a lógica do calendário ou a duração do módulo.")
    return current_date

# NOVA FUNÇÃO PÚBLICA (garante que todas as funções de navegação estão disponíveis)
def get_academic_date_after(start_date: date, num_days: int) -> date:
    """
    Calcula uma data que está 'num_days' dias acadêmicos depois de 'start_date'.
    Usa a função is_academic_recess completa.
    """
    current_date = start_date
    days_counted = 0
    safety_counter = 0
    max_safety_days = 365 * 2
    while days_counted < num_days:
        current_date += timedelta(days=1)
        if not is_academic_recess(current_date): # Usa a is_academic_recess pública
            days_counted += 1
        safety_counter += 1
        if safety_counter > max_safety_days:
            raise ValueError(f"Não foi possível encontrar data acadêmica {num_days} dias depois de {start_date} dentro de {max_safety_days} dias calendário.")
    return current_date

# --- NOVA FUNÇÃO PÚBLICA PARA OBTER INFORMAÇÕES DO MÓDULO POR DATA FIXA ---
def get_module_info_by_fixed_dates(check_date: date) -> dict | None:
    """
    Retorna o número do módulo, data de início e fim com base nas datas de calendário fixas.
    Retorna None se a data não estiver em nenhum módulo definido para o ano.
    """
    year = check_date.year
    if year not in _FIXED_MODULE_BOUNDARIES:
        return None 

    for module in _FIXED_MODULE_BOUNDARIES[year]:
        if module["start_date"] <= check_date <= module["end_date"]:
            return module
    return None

# --- Funções Placeholder (inalteradas do seu código original) ---
def is_in_first_activity_cycle_no_submission(current_date: date, last_submission_date: date | None, first_activity_cycle_end_date: date) -> bool:
    if last_submission_date is None and current_date <= first_activity_cycle_end_date:
        return True
    return False

def has_recent_visual_interaction_in_cycle(last_visual_interaction_date: date | None, current_date: date) -> bool:
    if last_visual_interaction_date:
        academic_days = calculate_academic_days_between(last_visual_interaction_date, current_date)
        return academic_days <= THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS
    return False