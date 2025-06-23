namespace IaPioniers.Models
{
    public class StudentProfile
    {
        public string userId { get; set; }
        public string userName { get; set; }
        public string status { get; set; }
        public string lastAccessDate { get; set; }
        public int totalActivitiesDelivered { get; set; }
        public StudentCourseDetail[] coursesTaken { get; set; }
        public ActivityDiversityReport activityDiversityReport { get; set; }
        public GraphData daysWithoutAccessGraphData { get; set; }
        public Observation[] observations { get; set; }
    }
}
