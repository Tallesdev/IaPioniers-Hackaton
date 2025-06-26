// CoordenadorController.cs
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration; // Adicione este using

namespace IaPioniers.Controllers
{
    public class CoordenadorController : Controller
    {
        private readonly IConfiguration _configuration; // Injete IConfiguration

        public CoordenadorController(IConfiguration configuration) // Construtor para injeção
        {
            _configuration = configuration;
        }

        public IActionResult DashboardCoordenador()
        {
            // Lê a URL base da API do appsettings.json
            ViewBag.PythonApiBaseUrl = _configuration["PythonApiBaseUrl"];

            // Certifique-se de que a URL termina com uma barra, se a sua API esperar
            // Se "http://192.168.1.13:5000/api/" já termina, não precisa
            // Mas é bom garantir se você for concatenar caminhos:
            // if (!ViewBag.PythonApiBaseUrl.EndsWith("/"))
            // {
            //     ViewBag.PythonApiBaseUrl += "/";
            // }

            return View();
        }
    }
}