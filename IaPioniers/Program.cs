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

// --- Configuração de Logging (Já está OK, só reorganizando) ---
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();
builder.Logging.SetMinimumLevel(LogLevel.Debug); // Define o nível mínimo para DEBUG

// --- Injeção de Dependência de Serviços ---

// Serviço para mapeamento Professor-Curso (Singletone é OK, pois os dados são estáticos ou carregados uma vez)
builder.Services.AddSingleton<ProfessorCourseMappingService>();

// Configuração para o HttpClient que será injetado em ProfessorDashboardService
// USAR A URL DO APPSETTINGS.JSON para flexibilidade
builder.Services.AddHttpClient<IProfessorDashboardService, ProfessorDashboardService>(client =>
{
    // Acessa a URL base da API Python do appsettings.json
    // Use "PythonApiBaseUrl" ou o nome da sua chave no appsettings.json
    var pythonApiBaseUrl = builder.Configuration["PythonApiBaseUrl"];
    if (string.IsNullOrEmpty(pythonApiBaseUrl))
    {
        // Se a chave não for encontrada, use um fallback e logue um erro
        client.BaseAddress = new Uri("http://127.0.0.1:5000/api/"); // Fallback
        builder.Logging.Services.BuildServiceProvider().GetRequiredService<ILogger<Program>>()
            .LogError("PythonApiBaseUrl não configurada em appsettings.json. Usando fallback: http://127.0.0.1:5000/api/");
    }
    else
    {
        client.BaseAddress = new Uri(pythonApiBaseUrl);
        builder.Logging.Services.BuildServiceProvider().GetRequiredService<ILogger<Program>>()
            .LogInformation($"HttpClient para IProfessorDashboardService configurado com BaseAddress: {pythonApiBaseUrl}");
    }
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// Adicione aqui a configuração para IaPioniersApiService se ela for diferente e necessária
// (Se essa API é para outro propósito, mantenha-a separada. Se for o mesmo que IProfessorDashboardService, remova a duplicação)
/*
builder.Services.AddHttpClient<IaPioniersApiService>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["PythonApiSettings:BaseUrl"] ?? "http://127.0.0.1:5000");
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});
*/

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
app.UseStaticFiles();     // Permite servir arquivos estáticos (CSS, JS, imagens)

app.UseRouting();         // Habilita o roteamento

app.UseAuthentication();  // Habilita autenticação (Identity)
app.UseAuthorization();   // Habilita autorização

// --- Mapeamento de Rotas ---

// Mapeia rotas de controladores MVC (com views)
// Esta rota padrão deve encontrar ProfessorDashboardController
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

// Mapeia rotas de Razor Pages (se você as usa)
app.MapRazorPages();

// Mapeia rotas para controladores com o atributo [ApiController] (se houver APIs RESTful)
// Geralmente vem DEPOIS das rotas MVC tradicionais, ou você as separa claramente.
// Se seu ProfessorDashboardController NÃO tem [ApiController], esta linha não o afetaria.
app.MapControllers();

app.Run();
