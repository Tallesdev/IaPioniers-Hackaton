using IaPioniers.Models.ViewModels;
using IaPioniers.Models; // Garanta que este using está presente para a classe Course

namespace IaPioniers.Services
{
    public interface IProfessorDashboardService
    {
        Task<DashboardViewModel> GetProfessorDashboardDataAsync(string professorId);
        Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string id);

        // Agora, o tipo 'Course' deve ser reconhecido
        Task<List<Course>> GetCoursesAsync();

        Task<string> GetDashboardDataAsync(string professorId);
        Task<string> GenerateReportAsync(string reportType);
    }
}
