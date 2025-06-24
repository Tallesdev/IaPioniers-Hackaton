using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Newtonsoft.Json;
using System; // Necessário para Uri, Exception
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;

using IaPioniers.Models.Models_DB; // Mantenha se você usa esses modelos
using IaPioniers.Models.ViewModels; // Garanta que DashboardViewModel está neste namespace
using IaPioniers.Data; // Mantenha se você usa seu contexto de banco de dados

// Removi o namespace padrão para esta classe de exemplo,
// mas se você tiver um, mantenha-o. Ex: namespace IaPioniers.Controllers
public class DashboardController : Controller
{
    private readonly ApplicationDbContext _context; // Mantenha se você usa o DB Context
    private readonly HttpClient _httpClient;

    // Ajustei o construtor para aceitar IConfiguration para obter o BaseAddress da API Python
    public DashboardController(ApplicationDbContext context, IHttpClientFactory clientFactory, IConfiguration configuration)
    {
        _context = context; // Mantenha se você usa o DB Context
        _httpClient = clientFactory.CreateClient();
        // Use a configuração para obter o BaseAddress
        var pythonApiBaseUrl = configuration["PythonApiBaseUrl"];
        if (string.IsNullOrEmpty(pythonApiBaseUrl))
        {
            throw new ApplicationException("PythonApiBaseUrl não configurada em appsettings.json.");
        }
        _httpClient.BaseAddress = new Uri(pythonApiBaseUrl);
    }

    public async Task<IActionResult> Index()
    {
        // Exemplo de professor - substitua pela lógica de como você obtém o professor atual
        // Você pode obter o professorId da sessão, autenticação, ou de um parâmetro da URL, como fizemos no ProfessorDashboardController
        // Por agora, vamos usar um valor fixo para teste, como "João Silva" ou um user_id que você sabe que existe na sua API Python
        string professorIdToFetch = "João Silva"; // Use um professor_id que sua API Python reconheça
        // Se você precisa de um professor_id do tipo USER_XXXX, use:
        // string professorIdToFetch = "USER_0258B482B842"; // Exemplo de um user_id da sua saída CSV

        var viewModel = new DashboardViewModel
        {
            ProfessorNome = professorIdToFetch // Usa o ID do professor para o nome inicial
        };

        HttpResponseMessage dashboardDataResponse = null;

        try
        {
            // O endpoint da sua API Python é: /professor/dashboard-data?professor_id={professorId}
            dashboardDataResponse = await _httpClient.GetAsync($"professor/dashboard-data?professor_id={System.Uri.EscapeDataString(professorIdToFetch)}");

            if (dashboardDataResponse.IsSuccessStatusCode)
            {
                var content = await dashboardDataResponse.Content.ReadAsStringAsync();

                // *** CORREÇÃO AQUI: Use DashboardViewModel diretamente ***
                var pythonData = JsonConvert.DeserializeObject<DashboardViewModel>(content);

                if (pythonData != null)
                {
                    viewModel.ProfessorNome = pythonData.ProfessorNome; // Atualiza com o nome retornado pela API
                    viewModel.TotalStudents = pythonData.TotalStudents;
                    viewModel.StudentsAtRisk = pythonData.StudentsAtRisk;
                    viewModel.TotalActivities = pythonData.TotalActivities; // <<< DESCOMENTADO AQUI

                    viewModel.CurrentModuleInfo = pythonData.CurrentModuleInfo ?? new CurrentModuleInfoViewModel();

                    viewModel.CourseSummaries = pythonData.CourseSummaries ?? new List<CourseSummaryViewModel>();
                    viewModel.RecentActivities = pythonData.RecentActivities ?? new List<RecentActivityViewModel>(); // <<< DESCOMENTADO AQUI
                }
            }
            else
            {
                Console.WriteLine($"Erro ao obter dados do dashboard da API Python: {dashboardDataResponse.StatusCode}");
                Console.WriteLine($"Conteúdo do erro: {await dashboardDataResponse.Content.ReadAsStringAsync()}");
                ViewBag.ErrorMessage = $"Erro ao carregar dados do dashboard: {dashboardDataResponse.ReasonPhrase}";
            }
        }
        catch (HttpRequestException httpEx)
        {
            Console.WriteLine($"Erro de conexão com a API Python: {httpEx.Message}. Verifique se a API está rodando em {_httpClient.BaseAddress}");
            ViewBag.ErrorMessage = $"Erro de conexão com a API Python. Detalhes: {httpEx.Message}";
        }
        catch (JsonSerializationException jsonEx)
        {
            Console.WriteLine($"Erro na desserialização do JSON da API: {jsonEx.Message}");
            if (dashboardDataResponse != null)
            {
                Console.WriteLine($"JSON que causou o erro: {await dashboardDataResponse.Content.ReadAsStringAsync()}");
            }
            ViewBag.ErrorMessage = $"Erro ao processar dados da API. Detalhes: {jsonEx.Message}";
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Ocorreu um erro inesperado: {ex.Message}");
            ViewBag.ErrorMessage = $"Ocorreu um erro inesperado: {ex.Message}";
        }

        return View(viewModel);
    }
}
