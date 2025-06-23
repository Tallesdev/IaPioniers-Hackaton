using System.Data;

namespace IaPioniers.Models
{
    public class GraphData
    {
        public List<string> Labels { get; set; } = new List<string>();
        public List<Dataset> Datasets { get; set; } = new List<Dataset>();
    }
}
