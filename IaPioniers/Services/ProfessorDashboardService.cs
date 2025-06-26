using IaPioniers.Models.ViewModels;
using IaPioniers.Models; // Para a classe Course, CourseDetailedAnalystics
using Microsoft.Extensions.Configuration;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;
using System.Collections.Generic; // Para List<T>
using Microsoft.Extensions.Logging; // Para ILogger
using System; // Para DateTime.Now, Uri, NotImplementedException

namespace IaPioniers.Services
{
    // Implementa o serviço do dashboard do professor
    // A interface IProfessorDashboardService NÃO DEVE SER DEFINIDA AQUI NOVAMENTE.
    public class ProfessorDashboardService : IProfessorDashboardService
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<ProfessorDashboardService> _logger;
        private readonly string _pythonApiBaseUrl;

        // Construtor: Injeta HttpClient e IConfiguration
        public ProfessorDashboardService(HttpClient httpClient, IConfiguration configuration, ILogger<ProfessorDashboardService> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
            // Carrega a URL base da sua API Python diretamente da raiz do appsettings.json
            _pythonApiBaseUrl = configuration["PythonApiBaseUrl"];
            if (string.IsNullOrEmpty(_pythonApiBaseUrl))
            {
                _logger.LogError("A URL base da API Python (PythonApiBaseUrl) não está configurada em appsettings.json.");
                // Fallback para uma URL padrão se não configurado (apenas para desenvolvimento/teste)
                _pythonApiBaseUrl = "http://localhost:5000/api/";
            }
            // Garante que a URL base termina com uma barra
            if (!_pythonApiBaseUrl.EndsWith("/"))
            {
                _pythonApiBaseUrl += "/";
            }
            // Define o BaseAddress do HttpClient (uma única vez)
            _httpClient.BaseAddress = new Uri(_pythonApiBaseUrl);
            _logger.LogInformation($"Python API Base URL configurada e BaseAddress do HttpClient definido para: {_pythonApiBaseUrl}");
        }

        public async Task<DashboardViewModel> GetProfessorDashboardDataAsync(string professorId)
        {
            _logger.LogInformation($"[{DateTime.Now}] Iniciando GetProfessorDashboardDataAsync para o professor: {professorId}");

            // Constrói a URL completa para o endpoint do dashboard do professor na API Python
            // Como _pythonApiBaseUrl já termina com /api/, removemos o prefixo "/api/" daqui
            // O endpoint correto é professor/dashboard-data
            var requestUrl = $"professor/dashboard-data?professor_id={Uri.EscapeDataString(professorId)}"; // Usar Uri.EscapeDataString para codificar o ID
            _logger.LogInformation($"[{DateTime.Now}] Chamando API Python: {_httpClient.BaseAddress}{requestUrl}");

            try
            {
                // Faz a requisição GET à API Python
                var response = await _httpClient.GetAsync(requestUrl);

                // Lança uma exceção se a resposta não for bem-sucedida (status code 2xx)
                response.EnsureSuccessStatusCode();

                // Lê o conteúdo da resposta como uma string
                var jsonResponse = await response.Content.ReadAsStringAsync();
                _logger.LogDebug($"[{DateTime.Now}] Resposta da API Python recebida: {jsonResponse.Substring(0, Math.Min(jsonResponse.Length, 500))}...");

                // Desserializa a string JSON para o DashboardViewModel
                var viewModel = JsonConvert.DeserializeObject<DashboardViewModel>(jsonResponse);

                if (viewModel == null)
                {
                    _logger.LogWarning($"[{DateTime.Now}] Desserialização resultou em um ViewModel nulo para o professor: {professorId}. Retornando ViewModel vazio.");
                    return new DashboardViewModel
                    {
                        ProfessorNome = professorId,
                        CourseSummaries = new List<CourseSummaryViewModel>(),
                        StudentEvasionList = new List<StudentEvasionInfoViewModel>(),
                        RecentActivities = new List<RecentActivityViewModel>(),
                        CurrentModuleInfo = new CurrentModuleInfoViewModel(),
                        EvasionRiskCount = 0,
                        TotalActivities = 0,
                        TotalStudents = 0,
                        StudentsAtRisk = 0
                    };
                }

                _logger.LogInformation($"[{DateTime.Now}] Dados do dashboard desserializados com sucesso para o professor: {professorId}.");
                return viewModel;
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"[{DateTime.Now}] Erro de Requisição HTTP ao chamar a API Python para o professor {professorId} na URL: {_httpClient.BaseAddress}{requestUrl}. Detalhes: {httpEx.Message}");
                throw; // Re-lança a exceção para ser tratada no Controller
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"[{DateTime.Now}] Erro de Desserialização JSON da API Python para o professor {professorId}. Detalhes: {jsonEx.Message}");
                throw; // Re-lança a exceção
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"[{DateTime.Now}] Erro inesperado ao obter dados do dashboard para o professor {professorId}. Detalhes: {ex.Message}");
                throw; // Re-lança a exceção
            }
        }

        // --- Implementações dos métodos da interface (Stubs/Placeholders) ---

        public Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string id)
        {
            _logger.LogWarning($"[{DateTime.Now}] Método GetCourseDetailsAsync chamado para ID: {id}, mas não está implementado.");
            throw new NotImplementedException("GetCourseDetailsAsync não foi totalmente implementado. Adicione a lógica para buscar os detalhes de um curso.");
        }

        public Task<List<Course>> GetCoursesAsync()
        {
            _logger.LogWarning($"[{DateTime.Now}] Método GetCoursesAsync chamado, mas não está implementado. Retornando lista vazia.");
            return Task.FromResult(new List<Course>());
        }

        public async Task<DashboardViewModel> GetDashboardDataAsync(string professorId)
        {
            _logger.LogInformation($"[{DateTime.Now}] Método GetDashboardDataAsync chamado (stub). Reutilizando GetProfessorDashboardDataAsync para {professorId}.");
            return await GetProfessorDashboardDataAsync(professorId);
        }

        public Task<bool> GenerateReportAsync(string reportType)
        {
            _logger.LogWarning($"[{DateTime.Now}] Método GenerateReportAsync chamado para tipo: {reportType}, mas não está implementado. Retornando true (simulação de sucesso).");
            return Task.FromResult(true);
        }
    }
}
