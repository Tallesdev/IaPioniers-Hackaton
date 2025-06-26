using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Mvc;

namespace IaPioniers.Controllers
{
    public class AlunoPerfilController : Controller
    {
        public IActionResult PerfilAluno(string id)
        {
            ViewData["StudentId"] = id;

            var model = new DashboardViewModel();


            return View (model);
        }
    }
}

