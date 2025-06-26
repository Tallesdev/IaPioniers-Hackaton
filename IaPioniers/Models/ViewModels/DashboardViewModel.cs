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

        public List<StudentOverviewViewModel> StudentsOverviewList { get; set; }

        public string SelectedCourseName { get; set; }

        public DashboardViewModel()
        {
            CourseSummaries = new List<CourseSummaryViewModel>();
            RecentActivities = new List<RecentActivityViewModel>();
            StudentEvasionList = new List<StudentEvasionInfoViewModel>();
            StudentsOverviewList = new List<StudentOverviewViewModel>();
        }
    }

    public class CurrentModuleInfoViewModel
    {
        [JsonProperty("number")]
        public int Number { get; set; }

        [JsonProperty("start_date")]
        public DateTime StartDate { get; set; }

        [JsonProperty("end_date")]
        public DateTime EndDate { get; set; }

        [JsonProperty("display_name")]
        public string DisplayName { get; set; }
    }

    public class CourseSummaryViewModel
    {
        [JsonProperty("AverageEngagementScore")]
        public double AverageEngagementScore { get; set; }

        [JsonProperty("CourseName")]
        public string CourseName { get; set; }

        [JsonProperty("LastActivityDate")]
        public DateTime LastActivityDate { get; set; }

        [JsonProperty("StudentsAtRiskInCourse")]
        public int StudentsAtRiskInCourse { get; set; }

        [JsonProperty("StudentsInCourse")]
        public int StudentsInCourse { get; set; }
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
        [JsonProperty("studentId")]
        public string StudentId { get; set; }

        [JsonProperty("studentName")]
        public string StudentName { get; set; }

        [JsonProperty("courseName")]
        public string CourseName { get; set; }

        [JsonProperty("totalAccesses")]
        public int TotalAccesses { get; set; }

        [JsonProperty("daysWithoutAccess")]
        public int DaysWithoutAccess { get; set; }

        [JsonProperty("riskScore")]
        public int RiskScore { get; set; }

        [JsonProperty("evasionReasons")]
        public List<string> EvasionReasons { get; set; }

        public StudentEvasionInfoViewModel()
        {
            EvasionReasons = new List<string>();
        }
    }

    public class StudentOverviewViewModel
    {
        [JsonProperty("studentId")]
        public string StudentId { get; set; }

        [JsonProperty("studentName")]
        public string StudentName { get; set; }

        [JsonProperty("courseName")]
        public string CourseName { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("statusDetails")]
        public List<string> StatusDetails { get; set; }

        [JsonProperty("recentSubmission")]
        public string RecentSubmission { get; set; }

        public StudentOverviewViewModel()
        {
            StatusDetails = new List<string>();
        }
    }
}