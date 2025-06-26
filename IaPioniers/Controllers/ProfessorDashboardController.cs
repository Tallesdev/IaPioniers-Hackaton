using Microsoft.AspNetCore.Mvc;
using IaPioniers.Models.ViewModels; // Certifique-se de importar seus ViewModels
using IaPioniers.Services; // Certifique-se de importar seu IProfessorDashboardService
using System;
using System.Threading.Tasks;
using System.Net.Http; // Para HttpRequestException
using Microsoft.Extensions.Logging; // Adicionado para ILogger
using Newtonsoft.Json; // Adicionado: Necessário para JsonSerializationException
using System.Diagnostics; // Necessário para Activity.Current?.Id ou HttpContext.TraceIdentifier
using IaPioniers.Models; // Adicionado: Se ErrorViewModel estiver aqui
using System.Collections.Generic; // Para List<T>

namespace IaPioniers.Controllers
{
    // Removido [ApiController] pois este controlador serve Views.
    // Removido [Route("api/[controller]")] para usar o roteamento MVC padrão ou rotas absolutas explícitas.
    public class ProfessorDashboardController : Controller
    {
        private readonly IProfessorDashboardService _dashboardService;
        private readonly ILogger<ProfessorDashboardController> _logger; // Adicionado ILogger

        // Construtor para injeção de dependência do serviço e do logger
        public ProfessorDashboardController(IProfessorDashboardService dashboardService, ILogger<ProfessorDashboardController> logger)
        {
            _dashboardService = dashboardService;
            _logger = logger; // Injeta o logger
        }

        // Action para exibir o dashboard principal do professor (seu Index original)
        // Exemplo de uso: https://localhost:7053/ProfessorDashboard?professorId=João%20Silva
        [HttpGet("/ProfessorDashboard")] // Rota absoluta para acesso direto
        public async Task<IActionResult> Index([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Dashboard do Professor (Index) com ID: '{professorId}'");

            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            if (string.IsNullOrEmpty(professorId))
            {
                _logger.LogWarning("ID do professor não fornecido na URL da requisição (Index).");
                ViewBag.ErrorMessage = "ID do professor não fornecido. Por favor, especifique um ID de professor na URL.";
                return View("Error", errorModel);
            }

            try
            {
                // Chama o serviço para obter os dados do dashboard do professor
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados para o professor (Index): {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de dashboard para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados do dashboard obtidos com sucesso para o professor (Index): {professorId}. Renderizando View 'Index'.");
                // Passa os dados para a View padrão para esta ação (Index.cshtml)
                return View(dashboardData);
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro ao conectar à API Python para o professor (Index) {professorId}. Detalhes: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao conectar à API Python. Verifique se a API está em execução e o endereço base configurado corretamente. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API para o professor (Index) {professorId}. Detalhes: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o dashboard para o professor (Index) {professorId}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o dashboard. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }
        }

        // NOVA AÇÃO: Para exibir o dashboard "Resumo de Dados"
        // Exemplo de uso: https://localhost:7053/ProfessorDashboard/ResumoDeDados?professorId=João%20Silva
        [HttpGet("/ProfessorDashboard/ResumoDeDados")]
        public async Task<IActionResult> ResumoDeDados([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Resumo de Dados do Professor com ID: '{professorId}'.");
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            if (string.IsNullOrEmpty(professorId))
            {
                _logger.LogWarning("ID do professor não fornecido para ResumoDeDados.");
                ViewBag.ErrorMessage = "ID do professor não fornecido. Por favor, especifique um ID de professor na URL.";
                return View("Error", errorModel);
            }

            try
            {
                // Chama o serviço para obter os dados do dashboard do professor (os mesmos dados serão usados)
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos para ResumoDeDados para o professor: {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de resumo para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados de resumo obtidos com sucesso para o professor: {professorId}. Renderizando View 'ResumoDeDados'.");
                return View("ResumoDeDados", dashboardData); // Retorna a view "ResumoDeDados"
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro HTTP para ResumoDeDados do professor {professorId}: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro de conexão com a API para ResumoDeDados. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"Erro de JSON para ResumoDeDados do professor {professorId}: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API para ResumoDeDados. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Erro inesperado para ResumoDeDados do professor {professorId}: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o resumo. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }
        }
    }
}
