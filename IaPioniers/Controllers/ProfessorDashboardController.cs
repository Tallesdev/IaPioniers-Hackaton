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

        // Action para exibir o dashboard do professor
        // A rota será diretamente /ProfessorDashboard
        // Exemplo de uso: https://localhost:7053/ProfessorDashboard?professorId=João%20Silva
        [HttpGet("/ProfessorDashboard")] // Rota absoluta: acessível diretamente como /ProfessorDashboard
        public async Task<IActionResult> Index([FromQuery] string professorId)
        {
            _logger.LogInformation($"Requisição recebida para Dashboard do Professor com ID: '{professorId}'");

            // Helper para criar ErrorViewModel com RequestId
            var errorModel = new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier };

            // Valida se o ID do professor foi fornecido
            if (string.IsNullOrEmpty(professorId))
            {
                _logger.LogWarning("ID do professor não fornecido na URL da requisição.");
                ViewBag.ErrorMessage = "ID do professor não fornecido. Por favor, especifique um ID de professor na URL.";
                // Passa o errorModel para a view de erro
                return View("Error", errorModel);
            }

            try
            {
                // Chama o serviço para obter os dados do dashboard do professor
                var dashboardData = await _dashboardService.GetProfessorDashboardDataAsync(professorId);

                // Verifica se os dados foram retornados
                if (dashboardData == null)
                {
                    _logger.LogWarning($"Dados do dashboard nulos retornados para o professor: {professorId}.");
                    ViewBag.ErrorMessage = $"Não foram encontrados dados de dashboard para o professor: {professorId}.";
                    return View("Error", errorModel);
                }

                _logger.LogInformation($"Dados do dashboard obtidos com sucesso para o professor: {professorId}. Renderizando View.");
                // Passa os dados para a View
                return View("Index", dashboardData);
            }
            catch (HttpRequestException httpEx)
            {
                // Erro ao tentar se conectar ou receber resposta da API Python
                _logger.LogError(httpEx, $"Erro ao conectar à API Python para o professor {professorId}. Detalhes: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao conectar à API Python. Verifique se a API está em execução e o endereço base configurado corretamente. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                // Erro na desserialização do JSON
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API para o professor {professorId}. Detalhes: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                // Outros erros inesperados
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o dashboard para o professor {professorId}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o dashboard. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }
        }
    }
}
