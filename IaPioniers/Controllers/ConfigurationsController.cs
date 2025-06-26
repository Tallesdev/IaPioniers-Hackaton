using Microsoft.AspNetCore.Mvc;
using IaPioniers.Models.ViewModels;

namespace IaPioniers.Controllers
{
    public class ConfigurationsController : Controller
    {
        public IActionResult Index()
        {
            var viewModel = new ConfigurationViewModel
            {
                ProfessorNome = "Celso" // obtenha dinamicamente
            };

            ViewData["Title"] = "Configurações";
            return View(viewModel);
        }
    }
}
