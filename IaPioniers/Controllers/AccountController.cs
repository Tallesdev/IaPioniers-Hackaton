using IaPioniers.Models;
using IaPioniers.Models.ViewModels;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.AspNetCore.Hosting; // Adicionado para IWebHostEnvironment

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
            // Pega o caminho do arquivo do appsettings.json
            var mappingFilePath = _configuration["Authorization:ProfessorMappingFilePath"];

            if (string.IsNullOrEmpty(mappingFilePath))
            {
                throw new System.Exception("Caminho do arquivo de mapeamento de professores não configurado em appsettings.json (Authorization:ProfessorMappingFilePath).");
            }

            // ** IMPORTANTE: Usar ContentRootPath para obter o caminho base do projeto. **
            // Isso garante que o caminho seja sempre resolvido corretamente em relação à raiz do seu projeto.
            var fullPath = Path.Combine(_env.ContentRootPath, mappingFilePath);

            if (!System.IO.File.Exists(fullPath))
            {
                throw new System.Exception($"Arquivo de mapeamento de professores não encontrado em: {fullPath}");
            }

            try
            {
                var jsonContent = System.IO.File.ReadAllText(fullPath);
                // Como o JSON é um dicionário, queremos apenas as chaves (nomes dos professores)
                var mapping = JsonConvert.DeserializeObject<Dictionary<string, object>>(jsonContent);

                // Retorna apenas as chaves (nomes) do dicionário
                return new List<string>(mapping.Keys);
            }
            catch (System.Exception ex)
            {
                throw new System.Exception($"Erro ao carregar ou desserializar o arquivo de mapeamento de professores: {ex.Message}");
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
                // ** NOVA LÓGICA DE VALIDAÇÃO DE NOME **
                if (!_authorizedNames.Contains(model.NomeCompleto))
                {
                    ModelState.AddModelError("NomeCompleto", "Este nome não está autorizado para registro. Por favor, contate o administrador.");
                    return View(model); // Retorna a view com o erro
                }
                // ** FIM DA NOVA LÓGICA **

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
                    return RedirectToAction("Index", "Home");
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
