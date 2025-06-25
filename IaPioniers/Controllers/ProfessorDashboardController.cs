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

        // Action para exibir o dashboard principal do professor (agora o "Resumo de Dados")
        [HttpGet("/ProfessorDashboard")]
        public async Task<IActionResult> Index([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Dashboard do Professor (Index) com ID: '{professorId}'");
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            // Usar um professorId padrão se não fornecido para fins de teste
            if (string.IsNullOrEmpty(professorId))
            {
                professorId = "João Silva"; // Ou "Prof. Celso" para o protótipo
                _logger.LogInformation($"ID do professor não fornecido, usando padrão: '{professorId}'.");
            }

            try
            {
                // Chama o serviço para obter os dados do dashboard do professor
                // Assumimos que GetProfessorDashboardDataAsync agora retorna o DashboardViewModel
                // com TODOS os campos necessários, incluindo EvasionRiskCount e StudentEvasionList
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados para o professor: {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de dashboard para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados do dashboard obtidos com sucesso para o professor: {professorId}. Renderizando View 'Index'.");
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

        // Ação /ProfessorDashboard/ResumoDeDados será removida ou adaptada se necessário
        // Se você não precisa mais dela, pode removê-la para evitar duplicação.
        /*
        [HttpGet("/ProfessorDashboard/ResumoDeDados")]
        public IActionResult ResumoDeDados([FromQuery] string professorId)
        {
            // Esta ação agora é redundante se o Index exibir o mesmo conteúdo
            // Se precisar de uma tela separada, reavalie a necessidade e os dados.
            _logger.LogInformation($"Requisição para Resumo de Dados (separado) para professor: {professorId}.");
            return View("ResumoDeDados", new DashboardViewModel { ProfessorNome = professorId });
        }
        */
    }

    // A classe StudentEvasionInfoViewModel já deve estar definida em Models/ViewModels/DashboardViewModel.cs
    // Se não estiver, certifique-se de que está lá e não duplique aqui.
    // public class StudentEvasionInfoViewModel { ... }
}
