// IaPioniers.Services/ProfessorDashboardService.cs
using IaPioniers.Models;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Net.Http; // Importe para HttpClient
using System.Text.Json; // Importe para serialização/desserialização JSON

namespace IaPioniers.Services
{
    public class ProfessorDashboardService : IProfessorDashboardService
    {
        private readonly HttpClient _httpClient; // HttpClient injetado
        private readonly JsonSerializerOptions _jsonOptions; // Opções para JSON (opcional)

        // O HttpClient é injetado aqui pelo ASP.NET Core, já configurado com BaseAddress
        public ProfessorDashboardService(HttpClient httpClient)
        {
            _httpClient = httpClient;
            // Configurações para desserialização JSON (se precisar de maiúsculas/minúsculas diferentes)
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true // Importante se o JSON da sua API IA usa camelCase (padrão JS)
            };
        }

        public async Task<List<CourseSummary>> GetCoursesAsync()
        {
            try
            {
                // Chamada REAL para o endpoint da sua API IA local que lista as turmas do professor
                // Assumindo um endpoint como /api/v1/professor/courses ou /courses
                var response = await _httpClient.GetAsync("/courses"); // <--- Ajuste o endpoint da sua API IA
                response.EnsureSuccessStatusCode(); // Lança exceção se o status code não for 2xx

                var jsonString = await response.Content.ReadAsStringAsync();
                var courses = JsonSerializer.Deserialize<List<CourseSummary>>(jsonString, _jsonOptions);

                return courses ?? new List<CourseSummary>(); // Retorna lista vazia se for null
            }
            catch (HttpRequestException ex)
            {
                // Tratar erros de HTTP (conexão, servidor, etc.)
                Console.WriteLine($"Erro HTTP ao buscar turmas: {ex.Message}");
                throw new ApplicationException("Não foi possível conectar à API IA para buscar turmas.", ex);
            }
            catch (JsonException ex)
            {
                // Tratar erros de serialização/desserialização JSON
                Console.WriteLine($"Erro JSON ao processar turmas: {ex.Message}");
                throw new ApplicationException("Erro ao processar dados da API IA para turmas.", ex);
            }
            // Outros catch blocks para erros gerais
        }

        public async Task<ProfessorDashboardData> GetDashboardDataAsync(string courseId)
        {
            try
            {
                // Chamada REAL para o endpoint da sua API IA local que dá os dados do dashboard de uma turma
                // Assumindo um endpoint como /api/v1/professor/dashboard?course_id={id}
                var response = await _httpClient.GetAsync($"/dashboard-data?course_id={courseId}"); // <--- Ajuste o endpoint e o nome do parâmetro
                response.EnsureSuccessStatusCode();

                var jsonString = await response.Content.ReadAsStringAsync();
                var dashboardData = JsonSerializer.Deserialize<ProfessorDashboardData>(jsonString, _jsonOptions);

                return dashboardData ?? new ProfessorDashboardData();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"Erro HTTP ao buscar dados do dashboard para {courseId}: {ex.Message}");
                throw new ApplicationException($"Não foi possível conectar à API IA para buscar dados do dashboard da turma {courseId}.", ex);
            }
            catch (JsonException ex)
            {
                Console.WriteLine($"Erro JSON ao processar dados do dashboard para {courseId}: {ex.Message}");
                throw new ApplicationException($"Erro ao processar dados da API IA para o dashboard da turma {courseId}.", ex);
            }
        }

        public async Task<bool> GenerateReportAsync(string courseId)
        {
            try
            {
                // Chamada REAL para o endpoint da sua API IA local que gera relatórios
                // Se a sua API IA retornar um URL de download, você pode retornar esse URL string aqui
                // ou apenas um booleano de sucesso se o frontend for notificado de outra forma.
                var response = await _httpClient.GetAsync($"/generate-report?course_id={courseId}"); // <--- Ajuste o endpoint e o nome do parâmetro
                response.EnsureSuccessStatusCode();

                // Assumindo que a API IA retorna sucesso ou um link para download.
                // Se retornar um URL, você pode ler e retornar o URL:
                // var reportUrl = await response.Content.ReadAsStringAsync();
                // return reportUrl; // Se o retorno fosse string

                return true; // Sucesso na requisição à API IA
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"Erro HTTP ao gerar relatório para {courseId}: {ex.Message}");
                throw new ApplicationException($"Não foi possível gerar o relatório via API IA para a turma {courseId}.", ex);
            }
        }

        public async Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string courseId)
        {
            try
            {
                // Chamada REAL para o endpoint da sua API IA local para detalhes completos da turma
                // Assumindo um endpoint como /api/v1/course-details/{id}
                var response = await _httpClient.GetAsync($"/course-details/{courseId}"); // <--- Ajuste o endpoint
                response.EnsureSuccessStatusCode();

                var jsonString = await response.Content.ReadAsStringAsync();
                var detailedAnalytics = JsonSerializer.Deserialize<CourseDetailedAnalystics>(jsonString, _jsonOptions);

                return detailedAnalytics ?? new CourseDetailedAnalystics();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"Erro HTTP ao buscar detalhes da turma {courseId}: {ex.Message}");
                throw new ApplicationException($"Não foi possível conectar à API IA para buscar detalhes da turma {courseId}.", ex);
            }
            catch (JsonException ex)
            {
                Console.WriteLine($"Erro JSON ao processar detalhes da turma {courseId}: {ex.Message}");
                throw new ApplicationException($"Erro ao processar dados da API IA para detalhes da turma {courseId}.", ex);
            }
        }
    }
}