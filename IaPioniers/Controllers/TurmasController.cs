using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Mvc;

namespace IaPioniers.Controllers
{
    public class TurmasController : Controller
    {
        public IActionResult Index()
        {
            var viewModel = new TurmasIndexViewModel
            {
                ProfessorNome = "Celso", // Ou obtenha dinamicamente
                Turmas = new List<TurmaCardViewModel>
                {
                    new TurmaCardViewModel { TurmaNome = "Turma A", QuantidadeAlunos = 36 },
                    new TurmaCardViewModel { TurmaNome = "Turma B", QuantidadeAlunos = 20 },
                    new TurmaCardViewModel { TurmaNome = "Turma C", QuantidadeAlunos = 20 },
                    new TurmaCardViewModel { TurmaNome = "Turma D", QuantidadeAlunos = 20 }
                    // Adicione mais turmas conforme necessário
                }
            };

            ViewData["Title"] = "Turmas";
            return View(viewModel);
        }
    }
}
