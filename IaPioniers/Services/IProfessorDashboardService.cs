using IaPioniers.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace IaPioniers.Services
{
    public interface IProfessorDashboardService
    {
        Task<List<CourseSummary>> GetCoursesAsync();
        Task<ProfessorDashboardData> GetDashboardDataAsync(string courseId);
        Task<bool> GenerateReportAsync(string courseId); // Retorna bool ou caminho/URL do relatório
        Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string courseId);
    }
}