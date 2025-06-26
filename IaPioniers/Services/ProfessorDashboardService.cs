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
    public class ProfessorDashboardService : IProfessorDashboardService
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<ProfessorDashboardService> _logger;
        private readonly string _pythonApiBaseUrlCleaned; // Armazenará a URL base limpa

        // Construtor: Injeta HttpClient e IConfiguration
        public ProfessorDashboardService(HttpClient httpClient, IConfiguration configuration, ILogger<ProfessorDashboardService> logger)
        {
            _httpClient = httpClient;
            _logger = logger;

            // Carrega a URL base da sua API Python diretamente da raiz do appsettings.json
            string rawPythonApiBaseUrl = configuration["PythonApiBaseUrl"];

            if (string.IsNullOrEmpty(rawPythonApiBaseUrl))
            {
                _logger.LogError("A URL base da API Python (PythonApiBaseUrl) não está configurada em appsettings.json. Usando fallback padrão.");
                rawPythonApiBaseUrl = "http://localhost:5000/"; // Fallback padrão, ajuste conforme necessário
            }

            // Garante que a URL base NÃO termine com "/api/" se for o caso,
            // pois os Blueprints do Flask já adicionam "/api/"
            if (rawPythonApiBaseUrl.EndsWith("/api/", StringComparison.OrdinalIgnoreCase))
            {
                _pythonApiBaseUrlCleaned = rawPythonApiBaseUrl.Substring(0, rawPythonApiBaseUrl.Length - 5); // Remove "/api/"
            }
            else
            {
                _pythonApiBaseUrlCleaned = rawPythonApiBaseUrl;
            }

            // Garante que a URL base final termine com UMA ÚNICA barra
            if (!_pythonApiBaseUrlCleaned.EndsWith("/"))
            {
                _pythonApiBaseUrlCleaned += "/";
            }

            // Define o BaseAddress do HttpClient (uma única vez)
            _httpClient.BaseAddress = new Uri(_pythonApiBaseUrlCleaned);
            _logger.LogInformation($"Python API Base URL configurada e BaseAddress do HttpClient definido para: {_pythonApiBaseUrlCleaned}");
        }

        // Implementação do método para retornar a URL base da API Python limpa
        public string GetPythonApiBaseUrl()
        {
            return _pythonApiBaseUrlCleaned;
        }

        public async Task<DashboardViewModel> GetProfessorDashboardDataAsync(string professorId)
        {
            _logger.LogInformation($"[{DateTime.Now}] Iniciando GetProfessorDashboardDataAsync para o professor: {professorId}");

            // A URL da requisição AGORA DEVE COMEÇAR com "api/"
            var requestUrl = $"api/professor/dashboard-data?professor_id={Uri.EscapeDataString(professorId)}";
            _logger.LogInformation($"[{DateTime.Now}] Chamando API Python: {_httpClient.BaseAddress}{requestUrl}");

            try
            {
                var response = await _httpClient.GetAsync(requestUrl);
                response.EnsureSuccessStatusCode(); // Lança exceção para códigos de status HTTP de erro (4xx, 5xx)
                var jsonResponse = await response.Content.ReadAsStringAsync();

                // --- NOVO: Logar o JSON bruto recebido para depuração ---
                _logger.LogDebug($"[{DateTime.Now}] JSON bruto recebido da API Python para {professorId}: {jsonResponse}");
                // --- FIM NOVO ---

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
                throw;
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"[{DateTime.Now}] Erro de Desserialização JSON da API Python para o professor {professorId}. Detalhes: {jsonEx.Message}");
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"[{DateTime.Now}] Erro inesperado ao obter dados do dashboard para o professor {professorId}. Detalhes: {ex.Message}");
                throw;
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
