using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Newtonsoft.Json;
using System.Net.Http;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;
using IaPioniers.Models.Models_DB;
using IaPioniers.Models.ViewModels; // Adapte se necessário
using IaPioniers.Data; // ou o namespace onde sua classe ApplicationDbContext está

public class DashboardController : Controller
{
    private readonly ApplicationDbContext _context;
    private readonly HttpClient _httpClient;

    public DashboardController(ApplicationDbContext context, IHttpClientFactory clientFactory)
    {
        _context = context;
        _httpClient = clientFactory.CreateClient();
        _httpClient.BaseAddress = new Uri("http://localhost:5000"); // endereço da API Python
    }

    public async Task<IActionResult> Index()
    {
        //var usuarioId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

        //var professor = await _context.Professores
        //    .FirstOrDefaultAsync(p => p.ApplicationUserId == usuarioId);

        //if (professor == null)
        //    return Unauthorized();
        var professor = new Professor { Nome = "Celso" };
        string professorNome = professor.Nome;

        var response = await _httpClient.GetAsync($"/professor/course-summaries?professor_id={professorNome}");
        if (!response.IsSuccessStatusCode)
            return View(new DashboardViewModel());

        var content = await response.Content.ReadAsStringAsync();
        var cursos = JsonConvert.DeserializeObject<List<ResumoCursoModel>>(content);

        int totalAlunos = cursos.Sum(c => c.StudentsInCourse);
        int alunosEmRisco = cursos.Sum(c => c.StudentsAtRiskInCourse);

        var model = new DashboardViewModel
        {
            ProfessorNome = professor.Nome,
            TotalAlunos = totalAlunos,
            AlunosEmRisco = alunosEmRisco,
            NumeroAtividades = 0,
            AtividadesRecentes = new List<AtividadeModel>()
        };

        return View(model);
    }
}
