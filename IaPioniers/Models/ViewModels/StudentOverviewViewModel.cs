// File: Models/ViewModels/StudentOverviewViewModel.cs

using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace IaPioniers.Models.ViewModels
{
    // ViewModel para a página de visão geral de alunos
    public class StudentOverviewPageViewModel
    {
        public string ProfessorNome { get; set; }
        public List<string> AvailableCourses { get; set; } // Para o dropdown de cursos
        public List<StudentOverviewItemViewModel> Students { get; set; } // A lista de alunos a ser exibida

        // NOVO: Propriedade para manter o curso selecionado no dropdown
        public string SelectedCourseName { get; set; }

        public StudentOverviewPageViewModel()
        {
            AvailableCourses = new List<string>();
            Students = new List<StudentOverviewItemViewModel>();
        }
    }

    // ViewModel para cada item de aluno na lista da visão geral
    public class StudentOverviewItemViewModel
    {
        [JsonProperty("studentId")]
        public string StudentId { get; set; }

        [JsonProperty("studentName")]
        public string StudentName { get; set; }

        [JsonProperty("courseName")] // Nome do curso ao qual o aluno está associado (para filtragem)
        public string CourseName { get; set; }

        [JsonProperty("status")] // Ex: "Participando", "Atrasado", "Inativo"
        public string Status { get; set; }

        [JsonProperty("statusDetails")] // Lista de detalhes que compõem o status (opcional, para tooltips ou debug)
        public List<string> StatusDetails { get; set; }

        [JsonProperty("recentSubmission")] // Ex: "Última entrega há 5 dias", "Nenhuma Entrega"
        public string RecentSubmission { get; set; }

        public StudentOverviewItemViewModel()
        {
            StatusDetails = new List<string>();
        }
    }
}
