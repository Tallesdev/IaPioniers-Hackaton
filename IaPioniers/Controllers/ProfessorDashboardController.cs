using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity; // Para UserManager
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
    [Microsoft.AspNetCore.Authorization.Authorize] // Garante que apenas usuários autenticados possam acessar este controller
    public class ProfessorDashboardController : Controller
    {
        private readonly IProfessorDashboardService _dashboardService;
        private readonly ILogger<ProfessorDashboardController> _logger;
        private readonly UserManager<ApplicationUser> _userManager;

        public ProfessorDashboardController(IProfessorDashboardService dashboardService,
                                            ILogger<ProfessorDashboardController> logger,
                                            UserManager<ApplicationUser> userManager)
        {
            _dashboardService = dashboardService;
            _logger = logger;
            _userManager = userManager;
        }

        [HttpGet("/ProfessorDashboard")]
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
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados para o professor (Index): {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de dashboard para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados do dashboard obtidos com sucesso para o professor (Index): {professorId}. Renderizando View 'Index'.");
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

        [HttpGet("/ProfessorDashboard/ResumoDeDados")]
        public async Task<IActionResult> ResumoDeDados()
        {
            var currentUser = await _userManager.GetUserAsync(User);
            if (currentUser == null)
            {
                _logger.LogWarning("Usuário não autenticado tentando acessar o resumo de dados. Redirecionando para login.");
                return RedirectToAction("Login", "Account");
            }

            var professorIdToFetch = currentUser.NomeCompleto;
            _logger.LogInformation($"Requisição recebida para Resumo de Dados do Professor com ID: '{professorIdToFetch}'.");
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            try
            {
                // Adicionando log para depuração antes de chamar o serviço
                _logger.LogDebug($"Chamando GetProfessorDashboardDataAsync para o professor: {professorIdToFetch}");
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorIdToFetch);

                // Adicionando log para depuração após a chamada do serviço
                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados pelo serviço para ResumoDeDados para o professor: {professorIdToFetch}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de resumo para o professor: {professorIdToFetch}.";
                    return View("Error", errorModel);
                }
                else
                {
                    _logger.LogDebug($"Dados do dashboard recebidos do serviço para {professorIdToFetch}: " +
                                     $"ProfessorNome: {dashboardData.ProfessorNome}, " +
                                     $"TotalActivities: {dashboardData.TotalActivities}, " +
                                     $"TotalStudents: {dashboardData.TotalStudents}, " +
                                     $"StudentsAtRisk: {dashboardData.StudentsAtRisk}, " +
                                     $"CourseSummaries Count: {dashboardData.CourseSummaries?.Count ?? 0}, " +
                                     $"RecentActivities Count: {dashboardData.RecentActivities?.Count ?? 0}, " +
                                     $"EvasionRiskCount: {dashboardData.EvasionRiskCount}, " +
                                     $"StudentEvasionList Count: {dashboardData.StudentEvasionList?.Count ?? 0}");
                }

                _logger.LogInformation($"Dados de resumo obtidos com sucesso para o professor: {professorIdToFetch}. Renderizando View 'ResumoDeDados'.");
                return View("ResumoDeDados", dashboardData);
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro HTTP para ResumoDeDados do professor {professorIdToFetch}: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro de conexão com a API para ResumoDeDados. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"Erro de JSON para ResumoDeDados do professor {professorIdToFetch}: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API para ResumoDeDados. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o resumo para o professor {professorIdToFetch}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o resumo. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }
        }
    }
}
