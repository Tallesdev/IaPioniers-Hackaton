namespace IaPioniers.Models
{
    public class CourseWithStudents
    {
        public string courseId { get; set; }
        public string courseName { get; set; }
        public int studentsInCourse { get; set; }
        public int studentsAtRiskInCourse { get; set; }
        public string summaryDescription { get; set; }
        public StudentBasicInfo[] students { get; set; }
    }
}
