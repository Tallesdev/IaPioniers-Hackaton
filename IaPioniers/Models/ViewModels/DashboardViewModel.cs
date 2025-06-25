// File: Models/ViewModels/DashboardViewModel.cs

using System;
using System.Collections.Generic;
using IaPioniers.Controllers;
using Newtonsoft.Json; // Certifique-se de ter o pacote Newtonsoft.Json instalado no seu projeto C#

namespace IaPioniers.Models.ViewModels
{
    public class DashboardViewModel
    {
        [JsonProperty("professorNome")]
        public string ProfessorNome { get; set; }

        [JsonProperty("totalActivities")]
        public int TotalActivities { get; set; }

        [JsonProperty("totalStudents")]
        public int TotalStudents { get; set; }

        [JsonProperty("studentsAtRisk")]
        public int StudentsAtRisk { get; set; }

        [JsonProperty("currentModuleInfo")]
        public CurrentModuleInfoViewModel CurrentModuleInfo { get; set; }

        [JsonProperty("courseSummaries")]
        public List<CourseSummaryViewModel> CourseSummaries { get; set; }

        [JsonProperty("recentActivities")]
        public List<RecentActivityViewModel> RecentActivities { get; set; }
        public int EvasionRiskCount { get; internal set; }
        public List<StudentEvasionInfoViewModel> StudentEvasionList { get; internal set; }

        public DashboardViewModel()
        {
            CourseSummaries = new List<CourseSummaryViewModel>();
            RecentActivities = new List<RecentActivityViewModel>();
            CurrentModuleInfo = new CurrentModuleInfoViewModel(); // Inicializa para evitar NullReferenceException
        }
    }

    public class CurrentModuleInfoViewModel
    {
        [JsonProperty("number")]
        public int? Number { get; set; } // int? para permitir valores nulos

        [JsonProperty("start_date")]
        public string Start_date { get; set; } // Mantido como string, pode ser convertido para DateTime no frontend se necessário

        [JsonProperty("end_date")]
        public string End_date { get; set; } // Mantido como string

        [JsonProperty("display_name")]
        public string Display_name { get; set; }
    }

    public class CourseSummaryViewModel
    {
        [JsonProperty("CourseName")]
        public string CourseName { get; set; }

        [JsonProperty("StudentsInCourse")]
        public int StudentsInCourse { get; set; }

        [JsonProperty("StudentsAtRiskInCourse")]
        public int StudentsAtRiskInCourse { get; set; }

        [JsonProperty("AverageEngagementScore")]
        public decimal AverageEngagementScore { get; set; } // Use decimal para precisão

        [JsonProperty("LastActivityDate")]
        public string LastActivityDate { get; set; } // Mantido como string
    }

    public class RecentActivityViewModel
    {
        [JsonProperty("Acao")]
        public string Acao { get; set; }

        [JsonProperty("Status")]
        public string Status { get; set; }

        [JsonProperty("DataHora")]
        public DateTime DataHora { get; set; } // Pode ser desserializado diretamente para DateTime

        [JsonProperty("Usuario")]
        public string Usuario { get; set; }
    }
}
