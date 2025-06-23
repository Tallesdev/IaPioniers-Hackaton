namespace IaPioniers.Models
{
    public class ProfessorOverview
    {
        public string professorName { get; set; }
        public int totalCourses { get; set; }
        public int totalStudents { get; set; }
        public int studentsAtRiskCount { get; set; }
        public CourseSummary[] courses { get; set; }
}
}
