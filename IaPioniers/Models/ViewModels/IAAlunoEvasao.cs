namespace IaPioniers.Models.ViewModels
{
    public class IAAlunoEvasao
    {
        public string StudentName { get; set; }
        public string CourseName { get; set; }
        public double RiskScore { get; set; }
        public List<string> EvasionReasons { get; set; }
    }
}
