namespace IaPioniers.Models
{
    public class StudentSummary
    {
        public string userId { get; set; } = string.Empty;
        public string userName { get; set; } = string.Empty;
        public string courseId { get; set; } = string.Empty;
        public string courseName { get; set; } = string.Empty;
        public int totalAccesses { get; set; }
        public int daysWithoutAcess { get; set; }
        public float evasionProbability { get; set; }
        public string status { get; set; } = string.Empty;
    }
}
