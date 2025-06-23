// IaPioniers.Models/ProfessorCourseMapping.cs
namespace IaPioniers.Models
{
    public class ProfessorCourseMapping
    {
        public string ProfessorId { get; set; } = string.Empty;
        // O identificador do curso no JSON de mapeamento é o nome criptografado.
        public string CourseName { get; set; } = string.Empty;
    }
}