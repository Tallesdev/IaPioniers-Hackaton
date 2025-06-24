namespace IaPioniers.Models.ViewModels // Ou o namespace onde seu ResumoCursoModel está
{
    public class ResumoCursoModel
    {
        public int StudentsInCourse { get; set; }
        public int StudentsAtRiskInCourse { get; set; }
        public string CourseName { get; set; }
        public string LastActivityDate { get; set; } // Adicionado
        public double? AverageEngagementScore { get; set; } // Adicionado, use double? para permitir nulos
    }
}