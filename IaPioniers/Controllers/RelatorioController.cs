using IaPioniers.Models.Models_DB;
using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using System.Net.Http;
using System.Text.Json;
using System.Linq; // Para Distinct()
using Microsoft.Extensions.Configuration; // Para IConfiguration
using System.Threading.Tasks; // Para Task
using System; // Para Uri, Exception
using System.Collections.Generic; // Para List<T>, HashSet<T>
using Microsoft.AspNetCore.Authorization; // Para [Authorize]

namespace IaPioniers.Controllers
{
    [Authorize] // Ensures that only authenticated users can access this controller
    public class RelatorioController : Controller
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration;

        public RelatorioController(IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _httpClientFactory = httpClientFactory;
            _configuration = configuration;
        }

        // GET: Relatorio/Index
        public async Task<IActionResult> Index(string professorId)
        {
            if (string.IsNullOrEmpty(professorId))
            {
                ModelState.AddModelError("", "Nome do professor não fornecido. Não é possível carregar os cursos.");
                return View(new RelatorioCursoViewModel());
            }

            var cursosDisponiveis = await BuscarCursosDoProfessorNaAPI(professorId);
            Console.WriteLine($"[DEBUG C#] Cursos disponíveis após chamada à API para '{professorId}': {string.Join(", ", cursosDisponiveis)}");

            var viewModel = new RelatorioCursoViewModel
            {
                Cursos = cursosDisponiveis.Select(c => new SelectListItem
                {
                    Value = c,
                    Text = c
                }).ToList()
            };

            ViewBag.ProfessorId = professorId;

            return View(viewModel);
        }

        // POST: Relatorio/Gerar
        [HttpPost]
        public async Task<IActionResult> Gerar(RelatorioCursoViewModel model)
        {
            if (string.IsNullOrWhiteSpace(model.CursoSelecionado))
            {
                ModelState.AddModelError("", "Selecione um curso.");

                string currentProfessorName = User.Identity.Name;
                if (string.IsNullOrEmpty(currentProfessorName))
                {
                    currentProfessorName = "João Silva"; // Fallback for testing if user identity is not fully set up
                }
                model.Cursos = (await BuscarCursosDoProfessorNaAPI(currentProfessorName)).Select(c => new SelectListItem { Value = c, Text = c }).ToList();
                return View("Index", model);
            }

            var alunosEmRisco = await ObterDadosIA(model.CursoSelecionado);

            double mediaRiscoTurma = 0;
            if (alunosEmRisco != null && alunosEmRisco.Any())
            {
                mediaRiscoTurma = alunosEmRisco.Average(a => a.RiskScore);
            }
            ViewBag.MediaRiscoTurmaPorcentagem = mediaRiscoTurma * 100;

            var viewModel = new RelatorioTurmaCompletoViewModel
            {
                Turma = new Turma
                {
                    Codigo = "Virtual",
                    AnoLetivo = DateTime.Now.Year,
                    Curso = new Curso { Nome = model.CursoSelecionado },
                    Professores = new List<Professor>()
                },
                AlunosEmRisco = alunosEmRisco
            };

            return View("RelatorioGerado", viewModel);
        }

        // Method to fetch courses for a SPECIFIC professor (expects professor's FULL NAME)
        private async Task<List<string>> BuscarCursosDoProfessorNaAPI(string professorName)
        {
            var client = _httpClientFactory.CreateClient();
            var baseUrl = _configuration["PythonApiBaseUrl"].TrimEnd('/') + "/";

            // CORRECTION HERE: Explicitly adds the "/api/" prefix
            var url = $"{baseUrl}api/professor/dashboard-data?professor_id={Uri.EscapeDataString(professorName)}";

            // Declare and initialize cursosDoProfessor here
            var cursosDoProfessor = new HashSet<string>();

            try
            {
                var response = await client.GetAsync(url);

                if (!response.IsSuccessStatusCode)
                {
                    Console.WriteLine($"Warning: Failed to fetch dashboard for professor {professorName} (Status: {response.StatusCode}): {await response.Content.ReadAsStringAsync()}");
                    return new List<string>();
                }

                var json = await response.Content.ReadAsStringAsync();
                using (JsonDocument doc = JsonDocument.Parse(json))
                {
                    var root = doc.RootElement;

                    if (root.TryGetProperty("courseSummaries", out JsonElement courseSummariesElement) &&
                        courseSummariesElement.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var courseSummary in courseSummariesElement.EnumerateArray())
                        {
                            if (courseSummary.TryGetProperty("CourseName", out JsonElement courseNameElement))
                            {
                                var nome = courseNameElement.GetString();
                                if (!string.IsNullOrEmpty(nome))
                                {
                                    cursosDoProfessor.Add(nome);
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error fetching courses from API for professor {professorName}: {ex.Message}");
                return new List<string>();
            }
            Console.WriteLine($"Total courses found for professor {professorName}: {cursosDoProfessor.Count}");
            return cursosDoProfessor.ToList();
        }

        // ObterDadosIA FUNCTION: CORRECTION TO ADD /api/
        private async Task<List<IAAlunoEvasao>> ObterDadosIA(string courseName)
        {
            var client = _httpClientFactory.CreateClient();

            var baseUrl = _configuration["PythonApiBaseUrl"].TrimEnd('/') + "/";
            // CORRECTION HERE: Explicitly adds the "/api/" prefix
            var url = $"{baseUrl}api/evasion-report/evasion-report/at-risk-students?course_name={Uri.EscapeDataString(courseName)}";

            try
            {
                var response = await client.GetAsync(url);
                if (!response.IsSuccessStatusCode)
                {
                    Console.WriteLine($"Error in Python API when getting evasion data (Status: {response.StatusCode}): {await response.Content.ReadAsStringAsync()}");
                    return new List<IAAlunoEvasao>();
                }

                var json = await response.Content.ReadAsStringAsync();
                using (JsonDocument doc = JsonDocument.Parse(json))
                {
                    var root = doc.RootElement;
                    var alunos = new List<IAAlunoEvasao>();

                    if (root.TryGetProperty("atRiskStudents", out JsonElement atRiskStudentsElement) &&
                        atRiskStudentsElement.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var aluno in atRiskStudentsElement.EnumerateArray())
                        {
                            double rawRiskScore = aluno.GetProperty("riskScore").GetDouble();
                            double normalizedRiskScore = rawRiskScore / 100.0;
                            normalizedRiskScore = Math.Max(0, Math.Min(1, normalizedRiskScore));

                            alunos.Add(new IAAlunoEvasao
                            {
                                StudentName = aluno.GetProperty("studentName").GetString(),
                                CourseName = aluno.GetProperty("courseName").GetString(),
                                RiskScore = normalizedRiskScore,
                                EvasionReasons = aluno.GetProperty("evasionReasons").EnumerateArray()
                                    .Select(e => e.GetString()).ToList()
                            });
                        }
                    }
                    return alunos;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error querying IA: " + ex.Message);
                return new List<IAAlunoEvasao>();
            }
        }
    }
}
