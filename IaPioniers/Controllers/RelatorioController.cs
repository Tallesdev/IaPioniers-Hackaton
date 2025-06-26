using IaPioniers.Models.Models_DB;
using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using System.Net.Http;
using System.Text.Json;
using System.Linq; // Para Distinct()

namespace IaPioniers.Controllers
{
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
        public async Task<IActionResult> Index()
        {
            var cursosDisponiveis = await BuscarTodosCursosDaAPI();

            var viewModel = new RelatorioCursoViewModel
            {
                Cursos = cursosDisponiveis.Select(c => new SelectListItem
                {
                    Value = c,
                    Text = c
                }).ToList()
            };

            return View(viewModel);
        }

        // POST: Relatorio/Gerar
        [HttpPost]
        public async Task<IActionResult> Gerar(RelatorioCursoViewModel model)
        {
            if (string.IsNullOrWhiteSpace(model.CursoSelecionado))
            {
                ModelState.AddModelError("", "Selecione um curso.");
                // Recarrega a lista de cursos para não ficar vazia após o erro
                model.Cursos = (await BuscarTodosCursosDaAPI()).Select(c => new SelectListItem { Value = c, Text = c }).ToList();
                return View("Index", model);
            }

            var alunosEmRisco = await ObterDadosIA(model.CursoSelecionado);

            // Calcula a média de risco da turma aqui, APÓS obter os dados normalizados
            // Apenas se houver alunos em risco, para evitar divisão por zero
            double mediaRiscoTurma = 0;
            if (alunosEmRisco != null && alunosEmRisco.Any())
            {
                mediaRiscoTurma = alunosEmRisco.Average(a => a.RiskScore);
            }
            // Multiplicamos por 100 para ter a porcentagem para exibição
            // E passamos para o ViewModel para ser usado no gráfico da turma na View
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

        // FUNÇÃO ATUALIZADA: BuscarTodosCursosDaAPI()
        private async Task<List<string>> BuscarTodosCursosDaAPI()
        {
            var client = _httpClientFactory.CreateClient();
            var baseUrl = _configuration["PythonApiBaseUrl"].TrimEnd('/') + "/";
            var todosCursosUnicos = new HashSet<string>();

            // ***** LISTA DE IDs DE PROFESSORES BASEADA NO JSON QUE VOCÊ FORNECEU *****
            var professorIds = new List<string>
            {
                "João Silva",
                "Maria Oliveira",
                "Pedro Souza",
                "Ana Costa"
            };

            if (!professorIds.Any())
            {
                Console.WriteLine("Nenhum ID de professor configurado para buscar cursos. A lista de cursos será vazia.");
                return new List<string>();
            }

            foreach (var professorId in professorIds)
            {
                var url = $"{baseUrl}professor/dashboard-data?professor_id={Uri.EscapeDataString(professorId)}";

                try
                {
                    var response = await client.GetAsync(url);

                    if (!response.IsSuccessStatusCode)
                    {
                        Console.WriteLine($"Aviso: Falha ao buscar dashboard para professor {professorId} (Status: {response.StatusCode}): {await response.Content.ReadAsStringAsync()}");
                        continue; // Tentar o próximo professor
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
                                        todosCursosUnicos.Add(nome);
                                    }
                                }
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Erro ao buscar cursos da API para professor {professorId}: {ex.Message}");
                    // Continuar para o próximo professor, se houver
                }
            }
            Console.WriteLine($"Total de cursos únicos encontrados: {todosCursosUnicos.Count}");
            return todosCursosUnicos.ToList();
        }

        // FUNÇÃO ObterDadosIA: CORRIGIDA PARA NORMALIZAR O RiskScore
        private async Task<List<IAAlunoEvasao>> ObterDadosIA(string courseName)
        {
            var client = _httpClientFactory.CreateClient();

            var baseUrl = _configuration["PythonApiBaseUrl"].TrimEnd('/') + "/";
            var url = $"{baseUrl}evasion-report/evasion-report/at-risk-students?course_name={Uri.EscapeDataString(courseName)}";

            try
            {
                var response = await client.GetAsync(url);
                if (!response.IsSuccessStatusCode)
                {
                    Console.WriteLine($"Erro na API Python ao obter dados de evasão (Status: {response.StatusCode}): {await response.Content.ReadAsStringAsync()}");
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

                            // ***** LINHA DE CORREÇÃO PRINCIPAL *****
                            // Assumimos que o 1500 significa 15% e 2000 significa 20%,
                            // então precisamos dividir por 10000 para obter 0.15 e 0.20
                            double normalizedRiskScore = rawRiskScore / 100.0;

                            // Garantir que o score esteja entre 0 e 1, caso a API envie algo maluco
                            normalizedRiskScore = Math.Max(0, Math.Min(1, normalizedRiskScore));

                            alunos.Add(new IAAlunoEvasao
                            {
                                StudentName = aluno.GetProperty("studentName").GetString(),
                                CourseName = aluno.GetProperty("courseName").GetString(),
                                RiskScore = normalizedRiskScore, // Usar o valor normalizado
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
                Console.WriteLine("Erro ao consultar IA: " + ex.Message);
                return new List<IAAlunoEvasao>();
            }
        }
    }
}