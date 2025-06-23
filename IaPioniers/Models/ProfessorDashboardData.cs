// IaPioniers.Models/ProfessorDashboardData.cs
using System.Collections.Generic;

namespace IaPioniers.Models
{
    public class ProfessorDashboardData
    {
        // Armazena o nome criptografado do curso selecionado (que é o seu identificador).
        public string SelectedCourseName { get; set; } = string.Empty;

        public int StudentsAtRiskInSelectedCourse { get; set; }
        public List<StudentSummary> StudentList { get; set; } = new List<StudentSummary>();
    }
}