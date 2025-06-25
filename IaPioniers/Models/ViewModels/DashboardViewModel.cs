// File: Models/ViewModels/DashboardViewModel.cs

using System;
using System.Collections.Generic;
using Newtonsoft.Json;

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

        [JsonProperty("evasionRiskCount")]
        public int EvasionRiskCount { get; set; }

        [JsonProperty("studentEvasionList")]
        public List<StudentEvasionInfoViewModel> StudentEvasionList { get; set; }

        public DashboardViewModel()
        {
            CourseSummaries = new List<CourseSummaryViewModel>();
            RecentActivities = new List<RecentActivityViewModel>();
            CurrentModuleInfo = new CurrentModuleInfoViewModel();
            StudentEvasionList = new List<StudentEvasionInfoViewModel>();
        }
    }

    public class CurrentModuleInfoViewModel
    {
        [JsonProperty("number")]
        public int? Number { get; set; }

        [JsonProperty("start_date")]
        public string Start_date { get; set; }

        [JsonProperty("end_date")]
        public string End_date { get; set; }

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
        public decimal AverageEngagementScore { get; set; }

        [JsonProperty("LastActivityDate")]
        public string LastActivityDate { get; set; }
    }

    public class RecentActivityViewModel
    {
        [JsonProperty("Acao")]
        public string Acao { get; set; }

        [JsonProperty("Status")]
        public string Status { get; set; }

        [JsonProperty("DataHora")]
        public DateTime DataHora { get; set; }

        [JsonProperty("Usuario")]
        public string Usuario { get; set; }
    }

    public class StudentEvasionInfoViewModel
    {
        [JsonProperty("StudentName")]
        public string StudentName { get; set; }

        [JsonProperty("CourseName")] // NOVA PROPRIEDADE
        public string CourseName { get; set; }

        [JsonProperty("TotalAccesses")]
        public int TotalAccesses { get; set; }

        [JsonProperty("DaysWithoutAccess")]
        public int DaysWithoutAccess { get; set; }

        [JsonProperty("EvasionProbability")]
        public int EvasionProbability { get; set; }
    }
}
