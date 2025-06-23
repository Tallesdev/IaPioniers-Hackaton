# evasion_reports.py
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app

def get_overall_evasion_report(df_risk_scores: pd.DataFrame) -> dict:
    if df_risk_scores.empty:
        return {
            "total_students": 0,
            "at_risk_students": 0,
            "at_risk_percentage": 0.0,
            "top_reasons": []
        }

    total_students = df_risk_scores['user_id'].nunique()
    at_risk_students_df = df_risk_scores[df_risk_scores['is_at_risk'] == True]
    at_risk_students_count = at_risk_students_df['user_id'].nunique()

    at_risk_percentage = (at_risk_students_count / total_students * 100) if total_students > 0 else 0.0

    all_reasons = []
    for reasons_list in at_risk_students_df['evasion_reasons']:
        if isinstance(reasons_list, list):
            all_reasons.extend(reasons_list)

    reason_counts = pd.Series(all_reasons).value_counts().to_dict()
    top_reasons = [{"reason": reason, "count": count} for reason, count in reason_counts.items()]
    top_reasons = sorted(top_reasons, key=lambda x: x['count'], reverse=True)[:5]

    return {
        "total_students": total_students,
        "at_risk_students": at_risk_students_count,
        "at_risk_percentage": round(at_risk_percentage, 2),
        "top_reasons": top_reasons
    }

def get_evasion_risk_students_for_professor(df_risk_scores: pd.DataFrame, df_features: pd.DataFrame, professor_id: str = None, course_name: str = None) -> dict:
    """
    Retorna a lista de alunos em risco de evasão associados a um professor ou curso específico.
    Agora usa o mapeamento professor-curso.
    """
    if df_risk_scores.empty or df_features.empty:
        return {
            "message": "Dados de scores de risco ou features não disponíveis.",
            "students_at_risk": []
        }

    filtered_course_identifiers = [] # Renomeado para clareza, pois serão course_fullname
    if professor_id:
        professor_course_mapping = current_app.config.get('PROFESSOR_COURSE_MAPPING')

        if not professor_course_mapping:
            return {
                "message": "Mapeamento professor-curso não carregado. Não é possível filtrar por professor_id.",
                "students_at_risk": []
            }

        filtered_course_identifiers = professor_course_mapping.get(professor_id, [])

        if not filtered_course_identifiers:
            return {
                "message": f"Professor ID '{professor_id}' não encontrado no mapeamento ou não possui cursos associados.",
                "students_at_risk": []
            }

        print(f"Identificadores de curso (fullname) encontrados para o professor {professor_id}: {filtered_course_identifiers}")

    elif course_name:
        # Esta parte já funciona buscando no 'course_fullname'
        # E retorna 'course_id', mas como 'course_id' é 'UNKNOWN', manteremos a filtragem final por 'course_fullname'
        # no próximo passo.
        matching_courses_df = df_features[df_features['course_fullname'].astype(str) == course_name]
        filtered_course_identifiers = matching_courses_df['course_fullname'].unique().tolist() # Pegar fullname para usar no filtro abaixo

        if not filtered_course_identifiers:
            return {
                "message": f"Nenhum curso encontrado com o nome '{course_name}'.",
                "students_at_risk": []
            }
    else:
        return {
            "message": "Por favor, forneça 'professor_id' ou 'course_name'.",
            "students_at_risk": []
        }

    # *** AQUI ESTÁ A MUDANÇA CRÍTICA: Filtrar por 'course_fullname' ***
    df_features_courses_relevant = df_features[
        df_features['course_fullname'].astype(str).isin(filtered_course_identifiers)
    ][[
        'user_id', 'course_id', 'course_fullname', 'course_category_name',
        'days_since_last_access_course', 'course_total_actions',
        'viewed_count_course', 'graded_count_course'
    ]].drop_duplicates(subset=['user_id', 'course_fullname']).copy() # Mudança aqui também para drop_duplicates por course_fullname


    if df_features_courses_relevant.empty:
        return {
            "message": f"Nenhum dado de feature encontrado para os cursos: {', '.join(filtered_course_identifiers)}.",
            "students_at_risk": []
        }

    df_combined_data = pd.merge(
        df_risk_scores,
        df_features_courses_relevant,
        on='user_id',
        how='inner'
    )

    if df_combined_data.empty:
        return {
            "message": "Nenhum dado combinado encontrado para os critérios de professor/curso.",
            "students_at_risk": []
        }

    risky_students_in_course = df_combined_data[
        (df_combined_data['is_at_risk'] == True)
    ].copy()

    students_list = []
    for index, row in risky_students_in_course.iterrows():
        students_list.append({
            "user_id": str(row['user_id']),
            "user_name": str(row['user_name']),
            "overall_evasion_score": float(row['overall_evasion_score']),
            # Mantenha course_id aqui, mesmo que seja UNKNOWN, para compatibilidade
            "course_id": str(row['course_id']), 
            "course_fullname": str(row['course_fullname']),
            "course_category_name": str(row['course_category_name']),
            "evasion_reasons": list(row['evasion_reasons']),
            "days_since_last_access_course": int(row.get('days_since_last_access_course', -1)),
            "course_total_actions": int(row.get('course_total_actions', 0)),
            "viewed_count_course": int(row.get('viewed_count_course', 0)),
            "graded_count_course": int(row.get('graded_count_course', 0))
        })

    return {
        "message": f"Alunos em risco para o {'professor' if professor_id else 'curso'} {professor_id if professor_id else course_name}",
        "students_at_risk": students_list
    }