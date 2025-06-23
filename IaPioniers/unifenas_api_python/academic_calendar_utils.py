# academic_calendar_utils.py
from datetime import date, datetime, timedelta

# Datas de recesso fixas
RECESS_START_DEC = date(1, 12, 20) # 20 de Dezembro
RECESS_END_MAR = date(1, 3, 8)     # 8 de Março
RECESS_START_JUL = date(1, 7, 1)   # 1 de Julho
RECESS_END_JUL = date(1, 7, 31)    # 31 de Julho

# Novo threshold de inatividade aceitável para uso em evasion_prediction_logic
THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS = 3 # Inatividade aceitável se houve visualização

def is_academic_recess(check_date: date) -> bool:
    """
    Verifica se uma dada data cai em um período de recesso acadêmico.
    Desconsidera o ano da data para recessos fixos por mês/dia.
    """
    month_day = (check_date.month, check_date.day)

    # Recesso de Julho
    if RECESS_START_JUL.month <= month_day[0] <= RECESS_END_JUL.month and \
       (month_day[0] == RECESS_START_JUL.month and month_day[1] >= RECESS_START_JUL.day or \
        month_day[0] == RECESS_END_JUL.month and month_day[1] <= RECESS_END_JUL.day):
        return True

    # Recesso de Dezembro a Março (passa por ano novo)
    # Se a data for em Dezembro, verifica do RECESS_START_DEC até o fim do ano
    if month_day[0] == RECESS_START_DEC.month and month_day[1] >= RECESS_START_DEC.day:
        return True
    # Se a data for em Janeiro, Fevereiro ou início de Março
    if RECESS_END_MAR.month >= month_day[0] >= 1 and \
       (month_day[0] == RECESS_END_MAR.month and month_day[1] <= RECESS_END_MAR.day or \
        month_day[0] < RECESS_END_MAR.month):
        return True
        
    return False

def calculate_academic_days_between(start_date: date, end_date: date) -> int:
    """
    Calcula o número de dias acadêmicos entre duas datas, excluindo recessos.
    """
    count = 0
    current_date = start_date # CORREÇÃO: Removido .date()
    while current_date <= end_date:
        if not is_academic_recess(current_date):
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
    return calculate_academic_days_between(target_date, today)

# NOVO: Adicionando função para obter uma data X dias acadêmicos no passado
def get_academic_date_ago(start_date: date, num_days: int) -> date:
    """
    Calcula uma data que está 'num_days' dias acadêmicos antes de 'start_date'.
    """
    current_date = start_date
    days_counted = 0
    while days_counted < num_days:
        current_date -= timedelta(days=1)
        if not is_academic_recess(current_date):
            days_counted += 1
    return current_date

# NOVO: Adicionando função placeholder para resolver o AttributeError
def is_in_first_activity_cycle_no_submission(current_date: date, last_submission_date: date | None, first_activity_cycle_end_date: date) -> bool:
    """
    Verifica se o aluno está no primeiro ciclo de atividades sem ter feito nenhuma submissão.
    Esta é uma função placeholder. A lógica real precisa ser implementada
    com base nos critérios específicos do seu projeto para definir o \"primeiro ciclo de atividade\"
    e o que constitui \"nenhuma submissão\".
    """
    if last_submission_date is None and current_date <= first_activity_cycle_end_date:
        # Exemplo de lógica: Se não há submissão e estamos dentro do primeiro ciclo.
        return True
    return False

# NOVO: Adicionando função placeholder para has_recent_visual_interaction_in_cycle
def has_recent_visual_interaction_in_cycle(last_visual_interaction_date: date | None, current_date: date) -> bool:
    """
    Verifica se houve interação visual recente dentro do ciclo de atividades.
    Esta é uma função placeholder. A lógica real precisa ser implementada
    com base nos critérios específicos do seu projeto.
    """
    if last_visual_interaction_date:
        # Exemplo: Se a última interação visual foi nos últimos THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS
        # dias acadêmicos antes da data atual.
        academic_days = calculate_academic_days_between(last_visual_interaction_date, current_date)
        return academic_days <= THRESHOLD_RECENT_VISUAL_INTERACTION_DAYS
    return False