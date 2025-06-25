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
    public class ProfessorDashboardController : Controller
    {
        private readonly IProfessorDashboardService _dashboardService;
        private readonly ILogger<ProfessorDashboardController> _logger; // Adicionado ILogger

        public ProfessorDashboardController(IProfessorDashboardService dashboardService, ILogger<ProfessorDashboardController> logger)
        {
            _dashboardService = dashboardService;
            _logger = logger;
        }

        // Action para exibir o dashboard principal do professor (seu Index original)
        [HttpGet("/ProfessorDashboard")]
        public async Task<IActionResult> Index([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Dashboard do Professor com ID: '{professorId}'");
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            if (string.IsNullOrEmpty(professorId))
            {
                _logger.LogWarning("ID do professor não fornecido na URL da requisição.");
                ViewBag.ErrorMessage = "ID do professor não fornecido. Por favor, especifique um ID de professor na URL.";
                return View("Error", errorModel);
            }

            try
            {
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados para o professor: {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de dashboard para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados do dashboard obtidos com sucesso para o professor: {professorId}. Renderizando View.");
                return View(dashboardData);
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro ao conectar à API Python para o professor {professorId}. Detalhes: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao conectar à API Python. Verifique se a API está em execução e o endereço base configurado corretamente. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API para o professor {professorId}. Detalhes: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o dashboard para o professor {professorId}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o dashboard. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }
        }

        // NOVA AÇÃO: Para exibir o dashboard "Resumo de Dados"
        [HttpGet("/ProfessorDashboard/ResumoDeDados")]
        public IActionResult ResumoDeDados([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Resumo de Dados do Professor com ID: '{professorId}'");

            // Crie um ViewModel com dados de exemplo (ou obtenha de um serviço real)
            var viewModel = new DashboardViewModel // Ou um ViewModel mais específico como ResumoDeDadosViewModel
            {
                ProfessorNome = professorId ?? "Desconhecido", // Use o ID ou um fallback
                EvasionRiskCount = 10, // Dados de exemplo conforme o protótipo
                CourseSummaries = new List<CourseSummaryViewModel>
                {
                    new CourseSummaryViewModel { CourseName = "Turma A", StudentsInCourse = 30, StudentsAtRiskInCourse = 5, AverageEngagementScore = 85.5m, LastActivityDate = "2025-06-20" },
                    new CourseSummaryViewModel { CourseName = "Turma B", StudentsInCourse = 25, StudentsAtRiskInCourse = 2, AverageEngagementScore = 92.1m, LastActivityDate = "2025-06-22" }
                },
                StudentEvasionList = new List<StudentEvasionInfoViewModel> // Preencher com os dados da tabela
                {
                    new StudentEvasionInfoViewModel { StudentName = "Ana Paula Veronezi", TotalAccesses = 18, DaysWithoutAccess = 2, EvasionProbability = 10 },
                    new StudentEvasionInfoViewModel { StudentName = "Geovana Fernandes", TotalAccesses = 14, DaysWithoutAccess = 6, EvasionProbability = 30 },
                    new StudentEvasionInfoViewModel { StudentName = "Gabrielle Souza", TotalAccesses = 5, DaysWithoutAccess = 15, EvasionProbability = 75 },
                    new StudentEvasionInfoViewModel { StudentName = "Hiago Augusto Pereira", TotalAccesses = 18, DaysWithoutAccess = 2, EvasionProbability = 10 },
                    new StudentEvasionInfoViewModel { StudentName = "Maria Eduarda Marques", TotalAccesses = 16, DaysWithoutAccess = 4, EvasionProbability = 20 },
                    new StudentEvasionInfoViewModel { StudentName = "Talles Gabriel", TotalAccesses = 8, DaysWithoutAccess = 12, EvasionProbability = 60 }
                }
            };

            // Retorna a view "ResumoDeDados.cshtml" com o ViewModel
            return View("ResumoDeDados", viewModel);
        }
    }

    // Adicione esta classe se ela ainda não existir no seu projeto (geralmente em Models/ViewModels)
    // Se você já tem StudentEvasionInfoViewModel em outro lugar, não duplique.
    public class StudentEvasionInfoViewModel
    {
        public string StudentName { get; set; }
        public int TotalAccesses { get; set; }
        public int DaysWithoutAccess { get; set; }
        public int EvasionProbability { get; set; } // 0-100
    }
}
