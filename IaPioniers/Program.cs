using IaPioniers.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using IaPioniers.Data;
using IaPioniers.Models;
using IaPioniers.Models.Models_DB; // Mantenha se ApplicationUser está aqui
using System.Net.Http;
using System;
using Microsoft.Extensions.Logging; // Garantir import de ILogger

var builder = WebApplication.CreateBuilder(args);

// --- Configuração da Conexão com o Banco de Dados ---
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ??
                       throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

// --- Configuração do Identity (Autenticação/Autorização) ---
builder.Services.AddDefaultIdentity<ApplicationUser>(options =>
{
    options.SignIn.RequireConfirmedAccount = false;
    options.Password.RequireDigit = false;
    options.Password.RequiredLength = 6;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase = false;
    options.Password.RequireLowercase = false;
})
.AddRoles<IdentityRole>()
.AddEntityFrameworkStores<ApplicationDbContext>();

// --- Configuração de Logging ---
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();
builder.Logging.SetMinimumLevel(LogLevel.Debug); // Define o nível mínimo para DEBUG para depuração

// --- Injeção de Dependência de Serviços ---

// Serviço para mapeamento Professor-Curso (Singletone é OK, pois os dados são estáticos ou carregados uma vez)
builder.Services.AddSingleton<ProfessorCourseMappingService>();

// Configuração para o HttpClient que será injetado em ProfessorDashboardService
builder.Services.AddHttpClient<IProfessorDashboardService, ProfessorDashboardService>(client =>
{
    // CORREÇÃO AQUI: Acessa a URL base da API Python do appsettings.json com a chave correta
    var pythonApiBaseUrl = builder.Configuration["PythonApiBaseUrl"];

    if (string.IsNullOrEmpty(pythonApiBaseUrl))
    {
        // Fallback: Se a chave não for encontrada/configurada, usa um endereço padrão.
        client.BaseAddress = new Uri("http://localhost:5000/"); // Garantir que termina com '/'
    }
    else
    {
        // Se a chave for encontrada, define o BaseAddress.
        client.BaseAddress = new Uri(pythonApiBaseUrl);
    }
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// Adiciona suporte a controladores MVC (com Views)
builder.Services.AddControllersWithViews();
// Adiciona suporte a Razor Pages (se você as usa)
builder.Services.AddRazorPages();

// --- Construção do Aplicativo ---
var app = builder.Build();

// --- Configuração do Pipeline de Requisições HTTP ---

// Configura o middleware de tratamento de exceções para ambiente de Desenvolvimento
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage(); // Exibe erros detalhados em dev
}
else
{
    app.UseExceptionHandler("/Home/Error"); // Redireciona para /Home/Error em produção
    app.UseHsts();
}

app.UseHttpsRedirection(); // Redireciona HTTP para HTTPS
app.UseStaticFiles();      // Permite servir arquivos estáticos (CSS, JS, imagens)

app.UseRouting();          // Habilita o roteamento

app.UseAuthentication();   // Habilita autenticação (Identity)
app.UseAuthorization();    // Habilita autorização

// --- Mapeamento de Rotas ---

// Mapeia rotas de controladores MVC (com views)
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

// Mapeia rotas de Razor Pages (se você as usa)
app.MapRazorPages();

// Mapeia rotas para controladores com o atributo [ApiController] (se houver APIs RESTful)
app.MapControllers();

app.Run();
