// File: Controllers/StudentsController.cs

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity; // Para UserManager
using IaPioniers.Models; // Para ApplicationUser, ErrorViewModel
using IaPioniers.Models.ViewModels; // Para StudentOverviewPageViewModel, StudentOverviewItemViewModel
using IaPioniers.Services; // Para IProfessorDashboardService
using Microsoft.Extensions.Logging; // Para ILogger
using System;
using System.Net.Http; // Para HttpRequestException
using System.Threading.Tasks;
using System.Diagnostics; // Para Activity.Current?.Id ou HttpContext.TraceIdentifier
using Newtonsoft.Json; // Para desserialização JSON
using System.Collections.Generic; // Para List<T>
using System.Linq; // Para .Select e .OrderBy
using Microsoft.Extensions.Configuration; // Para acessar o professor_curso_mapping.json

namespace IaPioniers.Controllers
{
    [Microsoft.AspNetCore.Authorization.Authorize] // Garante que apenas usuários autenticados possam acessar este controller
    public class StudentsController : Controller
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IProfessorDashboardService _dashboardService; // Para obter a URL base da API Python
        private readonly ILogger<StudentsController> _logger;
        private readonly IHttpClientFactory _httpClientFactory; // Para criar HttpClients
        private readonly IConfiguration _configuration; // Para acessar o professor_curso_mapping.json

        public StudentsController(UserManager<ApplicationUser> userManager,
                                  IProfessorDashboardService dashboardService,
                                  ILogger<StudentsController> logger,
                                  IHttpClientFactory httpClientFactory,
                                  IConfiguration configuration) // Injetar IConfiguration
        {
            _userManager = userManager;
            _dashboardService = dashboardService;
            _logger = logger;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration; // Atribuir IConfiguration
        }

        // Action para exibir a lista de alunos
        // courseName é o filtro selecionado no dropdown.
        [HttpGet("/Students")]
        public async Task<IActionResult> Index([FromQuery] string courseName = null)
        {
            var currentUser = await _userManager.GetUserAsync(User);
            if (currentUser == null)
            {
                _logger.LogWarning("Usuário não autenticado tentando acessar a página de alunos. Redirecionando para login.");
                return RedirectToAction("Login", "Account");
            }

            // SEMPRE use o NomeCompleto do usuário autenticado como o professorId para a API Python
            var professorIdToFetch = currentUser.NomeCompleto;

            // Inicializa o ViewModel que será passado para a View
            var viewModel = new StudentOverviewPageViewModel
            {
                ProfessorNome = professorIdToFetch, // Define o nome do professor para a View
                SelectedCourseName = courseName // Mantém o curso selecionado no dropdown
            };

            // Para exibir erros na View
            string requestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
            var errorModel = new ErrorViewModel { RequestId = requestId };

            try
            {
                // 1. Obter a lista de cursos APENAS para o professor logado
                // Carrega o mapeamento de professor-curso do arquivo JSON
                var professorMappingFilePath = _configuration["Authorization:ProfessorMappingFilePath"];
                if (string.IsNullOrEmpty(professorMappingFilePath))
                {
                    _logger.LogError("Caminho do arquivo de mapeamento de professor-curso não configurado em appsettings.json.");
                    ViewBag.ErrorMessage = "Erro de configuração: Caminho do mapeamento de cursos não encontrado.";
                    return View("Error", errorModel);
                }

                Dictionary<string, List<string>> professorCourseMapping;
                try
                {
                    var fullPath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, professorMappingFilePath);
                    var jsonContent = await System.IO.File.ReadAllTextAsync(fullPath);
                    professorCourseMapping = JsonConvert.DeserializeObject<Dictionary<string, List<string>>>(jsonContent);
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"Erro ao carregar o arquivo de mapeamento de professor-curso em: {professorMappingFilePath}");
                    ViewBag.ErrorMessage = "Erro ao carregar mapeamento de cursos. Verifique os logs.";
                    return View("Error", errorModel);
                }

                // Filtrar os cursos com base no professor logado
                if (professorCourseMapping != null && professorCourseMapping.ContainsKey(professorIdToFetch))
                {
                    viewModel.AvailableCourses = professorCourseMapping[professorIdToFetch]
                                                    .OrderBy(c => c)
                                                    .ToList();
                    _logger.LogInformation($"Cursos filtrados para o professor '{professorIdToFetch}': {string.Join(", ", viewModel.AvailableCourses)}");
                }
                else
                {
                    _logger.LogWarning($"Professor '{professorIdToFetch}' não encontrado no mapeamento de cursos ou sem cursos associados.");
                    viewModel.AvailableCourses = new List<string>();
                }

                // 2. Obter a lista detalhada de alunos (com filtro de curso)
                using (var httpClient = _httpClientFactory.CreateClient())
                {
                    var pythonApiBaseUrl = _dashboardService.GetPythonApiBaseUrl(); // Obter a URL base do serviço
                    if (string.IsNullOrEmpty(pythonApiBaseUrl))
                    {
                        throw new ApplicationException("PythonApiBaseUrl não configurada em appsettings.json.");
                    }
                    httpClient.BaseAddress = new Uri(pythonApiBaseUrl);

                    var studentListApiUrl = $"api/students-overview/list?professor_id={Uri.EscapeDataString(professorIdToFetch)}";
                    // Adiciona o filtro de curso se um curso foi selecionado e não for "Todas as Turmas"
                    if (!string.IsNullOrEmpty(courseName) && courseName != "Todas as Turmas")
                    {
                        studentListApiUrl += $"&course_name={Uri.EscapeDataString(courseName)}";
                    }

                    _logger.LogInformation($"Chamando API Python para lista de alunos: {httpClient.BaseAddress}{studentListApiUrl}");
                    var studentListResponse = await httpClient.GetAsync(studentListApiUrl);

                    if (studentListResponse.IsSuccessStatusCode)
                    {
                        var jsonResponse = await studentListResponse.Content.ReadAsStringAsync();
                        var apiResponse = JsonConvert.DeserializeObject<StudentsOverviewApiResponse>(jsonResponse);
                        viewModel.Students = apiResponse?.Students ?? new List<StudentOverviewItemViewModel>();
                        _logger.LogInformation($"Lista de alunos obtida com sucesso. Total: {viewModel.Students.Count} alunos.");
                    }
                    else
                    {
                        var errorContent = await studentListResponse.Content.ReadAsStringAsync();
                        _logger.LogError($"Erro ao obter lista de alunos da API Python: {studentListResponse.StatusCode} - {studentListResponse.ReasonPhrase}. Detalhes: {errorContent}");
                        ViewBag.ErrorMessage = $"Erro ao carregar lista de alunos: {studentListResponse.ReasonPhrase}. Verifique os logs para mais detalhes.";
                        viewModel.Students = new List<StudentOverviewItemViewModel>(); // Garante que a lista não é nula
                    }
                }
            }
            catch (HttpRequestException httpEx)
            {
                _logger.LogError(httpEx, $"Erro de HTTP ao carregar a lista de alunos para o professor {professorIdToFetch}. Detalhes: {httpEx.Message}");
                ViewBag.ErrorMessage = $"Erro de conexão com a API Python ao carregar alunos. Detalhes: {httpEx.Message}";
                return View("Error", errorModel);
            }
            catch (JsonSerializationException jsonEx)
            {
                _logger.LogError(jsonEx, $"Erro na desserialização do JSON da API de alunos para o professor {professorIdToFetch}. Detalhes: {jsonEx.Message}");
                ViewBag.ErrorMessage = $"Erro ao processar dados da API de alunos. Detalhes: {jsonEx.Message}";
                return View("Error", errorModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"Ocorreu um erro inesperado ao carregar a lista de alunos para o professor {professorIdToFetch}. Detalhes: {ex.Message}");
                ViewBag.ErrorMessage = $"Ocorreu um erro inesperado ao carregar a lista de alunos. Detalhes: {ex.Message}";
                return View("Error", errorModel);
            }

            return View(viewModel);
        }

        // Classe auxiliar para desserializar a resposta da API Python (que tem a chave "students")
        public class StudentsOverviewApiResponse
        {
            [JsonProperty("students")]
            public List<StudentOverviewItemViewModel> Students { get; set; }
        }

        // Classe auxiliar para desserializar a resposta da API de nomes de curso
        // Esta classe não será mais usada diretamente para popular o dropdown,
        // mas pode ser útil se a API Python tiver um endpoint específico para cursos de professor.
        // Por enquanto, vamos carregar o mapeamento diretamente no controlador.
        public class CourseNamesApiResponse
        {
            [JsonProperty("courseNames")]
            public List<string> CourseNames { get; set; }
        }
    }
}
