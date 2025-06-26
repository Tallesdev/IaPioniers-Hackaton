using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity; // Para UserManager
using IaPioniers.Models; // Para ApplicationUser, ErrorViewModel
using IaPioniers.Models.ViewModels; // Para DashboardViewModel
using IaPioniers.Services; // Para IProfessorDashboardService
using Microsoft.Extensions.Logging; // Para ILogger
using System;
using System.Net.Http; // Para HttpRequestException
using System.Threading.Tasks;
using System.Diagnostics; // Para Activity.Current?.Id ou HttpContext.TraceIdentifier
using Newtonsoft.Json; // <--- ESTA LINHA É CRÍTICA PARA JsonSerializationException

namespace IaPioniers.Controllers // Certifique-se de que o namespace está correto
{
    [Microsoft.AspNetCore.Authorization.Authorize] // Garante que apenas usuários autenticados possam acessar este controller
    public class DashboardController : Controller
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IProfessorDashboardService _dashboardService;
        private readonly ILogger<DashboardController> _logger;

        public DashboardController(UserManager<ApplicationUser> userManager,
                                   IProfessorDashboardService dashboardService,
                                   ILogger<DashboardController> logger)
        {
            _userManager = userManager;
            _dashboardService = dashboardService;
            _logger = logger;
        }

        public async Task<IActionResult> Index()
        {
            var currentUser = await _userManager.GetUserAsync(User);
            if (currentUser == null)
            {
                _logger.LogWarning("Usuário não autenticado tentando acessar o dashboard. Redirecionando para login.");
                return RedirectToAction("Login", "Account");
            }

            // Obtém o NomeCompleto do professor logado
            var professorIdToFetch = currentUser.NomeCompleto;

            var viewModel = new DashboardViewModel
            {
                ProfessorNome = professorIdToFetch // Usa o nome do professor logado como valor inicial
            };

            // Para exibir erros na View
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            try
            {
                // Chama o serviço para obter os dados do dashboard do professor
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorIdToFetch);

                if (dashboardData != null)
                {
                    // Popula o ViewModel com os dados retornados pela API Python
                    viewModel.ProfessorNome = dashboardData.ProfessorNome;
                    viewModel.TotalStudents = dashboardData.TotalStudents;
                    viewModel.StudentsAtRisk = dashboardData.StudentsAtRisk;
                    viewModel.TotalActivities = dashboardData.TotalActivities;
                    viewModel.CurrentModuleInfo = dashboardData.CurrentModuleInfo ?? new CurrentModuleInfoViewModel();
                    viewModel.CourseSummaries = dashboardData.CourseSummaries ?? new List<CourseSummaryViewModel>();
                    viewModel.RecentActivities = dashboardData.RecentActivities ?? new List<RecentActivityViewModel>();
                    viewModel.EvasionRiskCount = dashboardData.EvasionRiskCount;
                    viewModel.StudentEvasionList = dashboardData.StudentEvasionList ?? new List<StudentEvasionInfoViewModel>();

                    _logger.LogInformation($"Dados do dashboard carregados com sucesso para o professor: {professorIdToFetch}");
                }
                else
                {
                    _logger.LogWarning($"Dados do dashboard nulos para o professor: {professorIdToFetch}. Exibindo dashboard vazio.");
                    ViewBag.ErrorMessage = "Não foi possível carregar os dados do dashboard. Tente novamente mais tarde.";
                }
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro de HTTP ao carregar o dashboard para o professor {professorIdToFetch}. Detalhes: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro de conexão com a API Python ao carregar o dashboard. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx) // JsonSerializationException é usada aqui
            {
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API do dashboard para o professor {professorIdToFetch}. Detalhes: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API do dashboard. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o dashboard para o professor {professorIdToFetch}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o dashboard. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }

            return View(viewModel);
        }
    }
}
