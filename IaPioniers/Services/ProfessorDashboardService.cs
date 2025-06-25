using IaPioniers.Models.ViewModels;
using IaPioniers.Models;
using Newtonsoft.Json;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration; // Para acessar configurações como a URL da API
using System; // Para ApplicationException
using System.Collections.Generic; // Para List<Course>
using Microsoft.Extensions.Logging; // Adicionado para ILogger

namespace IaPioniers.Services
{
    public class ProfessorDashboardService : IProfessorDashboardService
    {
        private readonly HttpClient _httpClient;
        private readonly string _pythonApiBaseUrl;
        private readonly ILogger<ProfessorDashboardService> _logger; // Adicionado ILogger

        public ProfessorDashboardService(HttpClient httpClient, IConfiguration configuration, ILogger<ProfessorDashboardService> logger)
        {
            _httpClient = httpClient;
            _logger = logger; // Injeta o logger

            // Obtenha a URL base da sua API Python do appsettings.json
            _pythonApiBaseUrl = configuration["PythonApiBaseUrl"];
            if (string.IsNullOrEmpty(_pythonApiBaseUrl))
            {
                _logger.LogError("PythonApiBaseUrl não configurada em appsettings.json. Por favor, adicione-a ou verifique o caminho.");
                throw new ApplicationException("PythonApiBaseUrl não configurada em appsettings.json.");
            }
            _httpClient.BaseAddress = new System.Uri(_pythonApiBaseUrl);
            _logger.LogInformation($"BaseAddress do HttpClient configurado para: {_pythonApiBaseUrl}");
        }

        public async Task<DashboardViewModel> GetProfessorDashboardDataAsync(string professorId)
        {
            // Codifica o ID do professor para ser seguro em URLs (ex: espaços para %20)
            var encodedProfessorId = System.Uri.EscapeDataString(professorId);
            // Constrói a URL para o endpoint da API Python
            var requestUrl = $"professor/dashboard-data?professor_id={encodedProfessorId}";
            _logger.LogInformation($"Fazendo requisição à API Python: {_httpClient.BaseAddress}{requestUrl}");

            try
            {
                var response = await _httpClient.GetAsync(requestUrl);
                response.EnsureSuccessStatusCode(); // Lança uma exceção para códigos de erro HTTP (4xx ou 5xx)

                var jsonResponse = await response.Content.ReadAsStringAsync();
                _logger.LogDebug($"Resposta JSON da API Python recebida: {jsonResponse}");

                // Deserializa o JSON para o DashboardViewModel
                var dashboardData = JsonConvert.DeserializeObject<DashboardViewModel>(jsonResponse);
                _logger.LogInformation("Dados do dashboard desserializados com sucesso.");
                return dashboardData;
            }
            catch (HttpRequestException ex)
            {
                // Erro ao tentar se conectar ou receber resposta da API Python
                _logger.LogError(ex, $"Erro HTTP ao buscar dados do dashboard para professor {professorId}. URL: {_httpClient.BaseAddress}{requestUrl}. Detalhes: {ex.Message}");
                throw; // Propagar a exceção para o controlador lidar
            }
            catch (JsonException ex)
            {
                _logger.LogError(ex, $"Erro de desserialização JSON para dados do dashboard do professor {professorId}. Detalhes: {ex.Message}");
                // Tenta logar o conteúdo que causou o erro de desserialização, se possível
                try
                {
                    var contentOnError = await _httpClient.GetAsync(requestUrl)?.Result?.Content?.ReadAsStringAsync();
                    _logger.LogDebug($"Conteúdo JSON que causou erro de desserialização: {contentOnError}");
                }
                catch { /* Ignora erros ao tentar ler o conteúdo novamente para evitar loops */ }
                throw; // Propagar a exceção
            }
            catch (Exception ex)
            {
                // Outros erros inesperados
                _logger.LogError(ex, $"Ocorreu um erro inesperado em GetProfessorDashboardDataAsync para professor {professorId}. Detalhes: {ex.Message}");
                throw; // Propagar a exceção
            }
        }

        // IMPLEMENTAÇÕES DE MÉTODOS FALTANTES QUE CAUSARAM ERRO CS0535
        // Adicionados como placeholders para resolver os erros de compilação.
        // Você precisará adicionar a lógica real para esses métodos conforme o necessário.

        public async Task<CourseDetailedAnalystics> GetCourseDetailsAsync(string id)
        {
            _logger.LogWarning("GetCourseDetailsAsync não foi totalmente implementado.");
            throw new NotImplementedException("GetCourseDetailsAsync não foi totalmente implementado. Adicione a lógica para buscar os detalhes de um curso.");
        }

        public Task<List<Course>> GetCoursesAsync()
        {
            _logger.LogWarning("GetCoursesAsync não foi implementado.");
            // Retorna uma lista vazia como placeholder para resolver o erro CS0535.
            // Você precisará implementar a lógica real para buscar a lista de cursos aqui.
            return Task.FromResult(new List<Course>());
        }

        public Task<string> GetDashboardDataAsync(string professorId)
        {
            _logger.LogWarning("GetDashboardDataAsync não foi implementado. Verifique se este método é necessário, ou se GetProfessorDashboardDataAsync já atende ao propósito.");
            throw new NotImplementedException("GetDashboardDataAsync não foi implementado. Verifique se este método é necessário, ou se GetProfessorDashboardDataAsync já atende ao propósito.");
        }

        public Task<string> GenerateReportAsync(string reportType)
        {
            _logger.LogWarning("GenerateReportAsync não foi implementado.");
            throw new NotImplementedException("GenerateReportAsync não foi implementado. Adicione a lógica para gerar relatórios.");
        }
    }
}
