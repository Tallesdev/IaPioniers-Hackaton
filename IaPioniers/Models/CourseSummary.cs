// IaPioniers.Models/CourseSummary.cs
using System;
using System.Collections.Generic;

namespace IaPioniers.Models
{
    public class CourseSummary
    {
        // Este é o identificador ÚNICO do curso, que é o nome criptografado.
        // Ele serve como "ID" e "Nome" ao mesmo tempo.
        public string CourseName { get; set; } = string.Empty;

        public int StudentsInCourse { get; set; }
        public int StudentsAtRiskInCourse { get; set; }
        public DateTime? LastActivityDate { get; set; }
        public float AverageEngagementScore { get; set; }
    }
}