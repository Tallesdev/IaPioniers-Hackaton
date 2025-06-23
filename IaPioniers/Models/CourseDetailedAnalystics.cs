// IaPioniers.Models/CourseDetailedAnalytics.cs
using System.Collections.Generic;

namespace IaPioniers.Models
{
    public class CourseDetailedAnalystics
    {
        // Identificador único do curso para a análise detalhada (o nome criptografado).
        public string CourseName { get; set; } = string.Empty;

        public List<StudentSummary> AllStudentsInCourse { get; set; } = new List<StudentSummary>();

        public GraphData EvasionRiskGraph { get; set; } = new GraphData();
        public GraphData PresenceGraph { get; set; } = new GraphData();
        public GraphData ActivityCountDistributionGraph { get; set; } = new GraphData();
        public GraphData EngagementPerDayDistributionGraph { get; set; } = new GraphData();
        public GraphData EvasionProbabilityDistributionGraph { get; set; } = new GraphData();
    }
}