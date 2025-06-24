namespace IaPioniers.Models.ViewModels
{
    public class ResumoCursoModel
    {
        public string CourseName { get; set; }
        public int StudentsInCourse { get; set; }
        public int StudentsAtRiskInCourse { get; set; }
        public string LastActivityDate { get; set; }
        public string AverageEngagementScore { get; set; }
    }
}
