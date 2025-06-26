using IaPioniers.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using IaPioniers.Data;
using IaPioniers.Models;
using IaPioniers.Models.Models_DB; 
using System.Net.Http;
using System;
using Microsoft.Extensions.Logging; 

var builder = WebApplication.CreateBuilder(args);


var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ??
                       throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));


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

// --- Configura��o de Logging ---
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();
builder.Logging.SetMinimumLevel(LogLevel.Debug); // Define o n�vel m�nimo para DEBUG para depura��o

// --- Inje��o de Depend�ncia de Servi�os ---

// Servi�o para mapeamento Professor-Curso (Singletone � OK, pois os dados s�o est�ticos ou carregados uma vez)
builder.Services.AddSingleton<ProfessorCourseMappingService>();

// Configura��o para o HttpClient que ser� injetado em ProfessorDashboardService
builder.Services.AddHttpClient<IProfessorDashboardService, ProfessorDashboardService>(client =>
{
    // CORRE��O AQUI: Acessa a URL base da API Python do appsettings.json com a chave correta
    var pythonApiBaseUrl = builder.Configuration["PythonApiBaseUrl"];

    if (string.IsNullOrEmpty(pythonApiBaseUrl))
    {
        // Fallback: Se a chave n�o for encontrada/configurada, usa um endere�o padr�o.
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
// Adiciona suporte a Razor Pages (se voc� as usa)
builder.Services.AddRazorPages();

// --- Constru��o do Aplicativo ---
var app = builder.Build();

// --- Configura��o do Pipeline de Requisi��es HTTP ---

// Configura o middleware de tratamento de exce��es para ambiente de Desenvolvimento
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage(); // Exibe erros detalhados em dev
}
else
{
    app.UseExceptionHandler("/Home/Error"); // Redireciona para /Home/Error em produ��o
    app.UseHsts();
}

app.UseHttpsRedirection(); // Redireciona HTTP para HTTPS
app.UseStaticFiles();      // Permite servir arquivos est�ticos (CSS, JS, imagens)

app.UseRouting();          // Habilita o roteamento

app.UseAuthentication();   // Habilita autentica��o (Identity)
app.UseAuthorization();    // Habilita autoriza��o

// --- Mapeamento de Rotas ---

// Mapeia rotas de controladores MVC (com views)
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Account}/{action=Login}/{id?}"); // Alterado para Account e Login

// Mapeia rotas de Razor Pages (se voc� as usa)
app.MapRazorPages();

// Mapeia rotas para controladores com o atributo [ApiController] (se houver APIs RESTful)
app.MapControllers();

app.Run();
