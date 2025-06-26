using IaPioniers.Models;
using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.AspNetCore.Hosting;
using Microsoft.CodeAnalysis.CSharp.Syntax; // Adicionado para IWebHostEnvironment

namespace IaPioniers.Controllers
{
    public class AccountController : Controller
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly SignInManager<ApplicationUser> _signInManager;
        private readonly IConfiguration _configuration;
        private readonly IWebHostEnvironment _env; // Injetado IWebHostEnvironment
        private readonly List<string> _authorizedNames;

        public AccountController(UserManager<ApplicationUser> userManager,
                                 SignInManager<ApplicationUser> signInManager,
                                 IConfiguration configuration,
                                 IWebHostEnvironment env) // Adicionado 'env' ao construtor
        {
            _userManager = userManager;
            _signInManager = signInManager;
            _configuration = configuration;
            _env = env; // Atribui a instância injetada

            // Carrega os nomes autorizados do arquivo JSON na inicialização do controller
            _authorizedNames = LoadAuthorizedNames();
        }

        private List<string> LoadAuthorizedNames()
        {
            // Caminho para o arquivo de mapeamento de professores
            var filePath = Path.Combine(_env.ContentRootPath, _configuration["Authorization:ProfessorMappingFilePath"]);

            if (!System.IO.File.Exists(filePath))
            {
                throw new System.IO.FileNotFoundException($"Arquivo de mapeamento de professores não encontrado em: {filePath}");
            }

            try
            {
                var jsonContent = System.IO.File.ReadAllText(filePath);
                var mapping = JsonConvert.DeserializeObject<Dictionary<string, List<string>>>(jsonContent);
                if (mapping != null)
                {
                    return new List<string>(mapping.Keys);
                }
                return new List<string>();
            }
            catch (JsonSerializationException ex)
            {
                // Este erro será mais específico se o JSON estiver malformado
                throw new System.Exception($"Erro ao carregar ou desserializar o arquivo de mapeamento de professores: {ex.Message}");
            }
            catch (System.Exception ex)
            {
                // Captura qualquer outra exceção inesperada
                throw new System.Exception($"Ocorreu um erro inesperado ao carregar o arquivo de mapeamento de professores: {ex.Message}");
            }
        }

        public IActionResult Login()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> Login(LoginViewModel model)
        {
            if (ModelState.IsValid)
            {

                var result = await _signInManager.PasswordSignInAsync(
                    model.Email, model.Senha, isPersistent: false, lockoutOnFailure: false);

                if (result.Succeeded)
                {
                    var user = await _userManager.FindByEmailAsync(model.Email);
<<<<<<< Talles(duda)
                    if (user != null)
                    {
                        // REDIRECIONA PARA ProfessorDashboard/ResumoDeDados PASSANDO O NOME COMPLETO DO USUÁRIO
                        return RedirectToAction("ResumoDeDados", "ProfessorDashboard", new { professorId = user.NomeCompleto });
                    }
                    // Se o usuário for nulo por algum motivo, redireciona para a home como fallback
=======
                    return RedirectToAction("ResumoDeDados", "ProfessorDashboard");
                }
                else
                {
>>>>>>> Duda(Talles)
                    return RedirectToAction("Index", "Home");
                }

                    ModelState.AddModelError("", "Login inválido. Verifique email e senha.");
            }
            return View(model);
        }

        public IActionResult Register()
        {
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> Register(RegisterViewModel model)
        {
            if (ModelState.IsValid)
            {
                // NOVA LÓGICA DE VALIDAÇÃO DE NOME
                if (!_authorizedNames.Contains(model.NomeCompleto))
                {
                    ModelState.AddModelError("NomeCompleto", "Este nome não está autorizado para registro. Por favor, contate o administrador.");
                    return View(model); // Retorna a view com o erro
                }
                // FIM DA NOVA LÓGICA

                var user = new ApplicationUser
                {
                    UserName = model.Email,
                    Email = model.Email,
                    NomeCompleto = model.NomeCompleto
                };

                var result = await _userManager.CreateAsync(user, model.Senha);

                if (result.Succeeded)
                {
                    // Por enquanto, apenas registra o usuário.
                    // A lógica de atribuição de roles de Coordenador/Administrador virá depois.
                    await _signInManager.SignInAsync(user, isPersistent: false);
<<<<<<< Talles(duda)
                    // REDIRECIONA PARA ProfessorDashboard/ResumoDeDados APÓS REGISTRO
                    return RedirectToAction("ResumoDeDados", "ProfessorDashboard", new { professorId = user.NomeCompleto });
=======
                    return RedirectToAction("ResumoDeDados", "ProfessorDashboard");
>>>>>>> Duda(Talles)
                }

                foreach (var error in result.Errors)
                    ModelState.AddModelError("", error.Description);
            }

            return View(model);
        }

        [HttpPost]
        public async Task<IActionResult> Logout()
        {
            await _signInManager.SignOutAsync();
            return RedirectToAction("Login", "Account");
        }
    }
}
