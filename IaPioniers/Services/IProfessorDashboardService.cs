using IaPioniers.Models.ViewModels; // Garanta que este using está presente para DashboardViewModel
using IaPioniers.Models; // Garanta que este using está presente para as classes Course e CourseDetailedAnalystics
using System.Collections.Generic; // Para List<T>
using System.Threading.Tasks; // Para Task

namespace IaPioniers.Services
{
    // ESTA DEVE SER A ÚNICA DEFINIÇÃO DA INTERFACE IProfessorDashboardService NO SEU PROJETO.
    public interface IProfessorDashboardService
    {
        Task<DashboardViewModel> GetProfessorDashboardDataAsync(string professorId);

        Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string id);

        Task<List<Course>> GetCoursesAsync();

        Task<DashboardViewModel> GetDashboardDataAsync(string professorId);

        Task<bool> GenerateReportAsync(string reportType);

        // NOVO: Adicione esta declaração para o método que retorna a URL base da API Python
        string GetPythonApiBaseUrl();
    }
}
