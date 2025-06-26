using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Newtonsoft.Json;
using System;
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;
using Microsoft.AspNetCore.Identity; // Necessário para UserManager
using IaPioniers.Models.Models_DB;
using IaPioniers.Models.ViewModels;
using IaPioniers.Data;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using IaPioniers.Models;

namespace IaPioniers.Controllers
{
    // Adicione o atributo [Authorize] para garantir que apenas usuários autenticados possam acessar este controller
    // Se você tiver roles definidas, poderá restringir ainda mais, por exemplo: [Authorize(Roles = "Professor")]
    [Microsoft.AspNetCore.Authorization.Authorize]
    public class DashboardController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly HttpClient _httpClient;
        private readonly UserManager<ApplicationUser> _userManager; // Injetado UserManager
        private readonly ILogger<DashboardController> _logger; // Para logging
        private readonly IConfiguration _configuration; // Para acessar configurações

        public DashboardController(ApplicationDbContext context,
                                   IHttpClientFactory clientFactory,
                                   UserManager<ApplicationUser> userManager, // Adicionado ao construtor
                                   ILogger<DashboardController> logger, // Adicionado logger
                                   IConfiguration configuration) // Adicionado configuration
        {
            _context = context;
            _userManager = userManager; // Atribui o UserManager
            _logger = logger; // Atribui o logger
            _configuration = configuration; // Atribui configuration

            _httpClient = clientFactory.CreateClient();
            var pythonApiBaseUrl = _configuration["PythonApiBaseUrl"];

            if (string.IsNullOrEmpty(pythonApiBaseUrl))
            {
                _logger.LogError("A URL base da API Python não está configurada em appsettings.json (PythonApiBaseUrl). Usando localhost:5000 como fallback.");
                // CORREÇÃO: Usar _httpClient aqui
                _httpClient.BaseAddress = new Uri("http://localhost:5000/");
            }
            else
            {
                // CORREÇÃO: Usar _httpClient aqui
                _httpClient.BaseAddress = new Uri(pythonApiBaseUrl);
            }
            // CORREÇÃO: Usar _httpClient aqui
            _httpClient.DefaultRequestHeaders.Add("Accept", "application/json");
        }

        public async Task<IActionResult> Index()
        {
            // 1. Obter o usuário logado atualmente
            var currentUser = await _userManager.GetUserAsync(User);

            if (currentUser == null)
            {
                // Se o usuário não estiver logado por algum motivo, redirecione para o login
                // Ou exiba uma mensagem de erro adequada.
                _logger.LogWarning("Tentativa de acessar o Dashboard sem usuário logado.");
                return RedirectToAction("Login", "Account");
            }

            // Usar o NomeCompleto do usuário logado para buscar os dados na API Python
            string professorIdToFetch = currentUser.NomeCompleto;
            _logger.LogInformation($"Usuário logado: {professorIdToFetch}. Buscando dados do dashboard.");

            var viewModel = new DashboardViewModel
            {
                ProfessorNome = professorIdToFetch // Usa o nome completo do professor logado
            };

            HttpResponseMessage dashboardDataResponse = null;

            try
            {
                // O endpoint da sua API Python é: /professor/dashboard-data?professor_id={professorId}
                dashboardDataResponse = await _httpClient.GetAsync($"professor/dashboard-data?professor_id={System.Uri.EscapeDataString(professorIdToFetch)}");

                if (dashboardDataResponse.IsSuccessStatusCode)
                {
                    var content = await dashboardDataResponse.Content.ReadAsStringAsync();
                    _logger.LogDebug($"Conteúdo da API Python recebido: {content}");

                    var pythonData = JsonConvert.DeserializeObject<DashboardViewModel>(content);

                    if (pythonData != null)
                    {
                        // Atualiza o ViewModel com os dados da API
                        viewModel.ProfessorNome = pythonData.ProfessorNome;
                        viewModel.TotalStudents = pythonData.TotalStudents;
                        viewModel.StudentsAtRisk = pythonData.StudentsAtRisk;
                        viewModel.TotalActivities = pythonData.TotalActivities;
                        viewModel.EvasionRiskCount = pythonData.EvasionRiskCount; // Certifique-se de que este campo está vindo da API
                        viewModel.CurrentModuleInfo = pythonData.CurrentModuleInfo ?? new CurrentModuleInfoViewModel();
                        viewModel.CourseSummaries = pythonData.CourseSummaries ?? new List<CourseSummaryViewModel>();
                        viewModel.RecentActivities = pythonData.RecentActivities ?? new List<RecentActivityViewModel>();
                        viewModel.StudentEvasionList = pythonData.StudentEvasionList ?? new List<StudentEvasionInfoViewModel>(); // Lista de evasão
                    }
                    else
                    {
                        _logger.LogWarning($"API Python retornou JSON nulo ou vazio para o professor: {professorIdToFetch}");
                        ViewBag.ErrorMessage = "Não foi possível processar os dados do dashboard (resposta vazia).";
                    }
                }
                else
                {
                    var errorContent = await dashboardDataResponse.Content.ReadAsStringAsync();
                    _logger.LogError($"Erro ao obter dados do dashboard da API Python: {dashboardDataResponse.StatusCode} - {dashboardDataResponse.ReasonPhrase}. Detalhes: {errorContent}");
                    ViewBag.ErrorMessage = $"Erro ao carregar dados do dashboard: {dashboardDataResponse.ReasonPhrase}. Verifique os logs para mais detalhes.";
                }
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro de conexão com a API Python para o professor {professorIdToFetch}. Verifique se a API está rodando em {_httpClient.BaseAddress}");
                ViewBag.ErrorMessage = $"Erro de conexão com a API Python. Detalhes: {httpEx.Message}.";
            }
            catch (JsonSerializationException jsonEx)
            {
                string rawJson = dashboardDataResponse != null ? await dashboardDataResponse.Content.ReadAsStringAsync() : "N/A";
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API para o professor {professorIdToFetch}. JSON recebido: {rawJson}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API. Detalhes: {jsonEx.Message}.";
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar o dashboard para o professor {professorIdToFetch}.");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar o dashboard. Detalhes: {ex.Message}.";
            }

            return View(viewModel);
        }
    }
}
