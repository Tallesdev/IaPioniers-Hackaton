using IaPioniers.Views.ViewModels;
using Microsoft.AspNetCore.Mvc;

namespace IaPioniers.Controllers
{
    public class AccountController : Controller
    {
        public IActionResult Login()
        {
            return View();
        }

        [HttpPost]
        public IActionResult Login(LoginViewModel model)
        {
            if (ModelState.IsValid)
            {
                // Lógica de autenticação aqui
                // Ex: chamar sua API de backend para validar as credenciais
                // Se sucesso, redirecionar para o Dashboard (Visão Geral)
                // Se falha, adicionar ModelState.AddModelError e retornar a View
            }
            return View(model); // Retorna a View com erros de validação
        }

        [HttpPost]
        public IActionResult Register(RegisterViewModel model)
        {
            if (ModelState.IsValid)
            {
                // Lógica de registro aqui
                // Ex: chamar sua API de backend para criar um novo usuário
                // Se sucesso, redirecionar para a tela de login ou Dashboard
                // Se falha, adicionar ModelState.AddModelError e retornar a View
            }
            return View(model); // Retorna a View com erros de validação
        }
    }

}
