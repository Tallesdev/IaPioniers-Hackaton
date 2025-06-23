namespace IaPioniers.Models
{
    public class Dataset
    {
        public string label { get; set; } = string.Empty;
        public List<float> Data { get; set; } = new List<float>();
        public string borderColor { get; set; } = string.Empty;
        public string backgroundColor { get; set; } = string.Empty;
    }
}
