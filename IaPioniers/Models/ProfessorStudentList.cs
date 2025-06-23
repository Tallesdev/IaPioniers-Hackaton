namespace IaPioniers.Models
{
    public class ProfessorStudentList
    {
        public string selectedCourseId { get; set; }
        public string searchTerm { get; set; }
        public StudentDetailedSummary[] students { get; set; }
}
}
