using IaPioniers.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using IaPioniers.Data;
using IaPioniers.Models;
using IaPioniers.Models.Models_DB;
using System.Net.Http;
using Microsoft.Extensions.Logging;

var builder = WebApplication.CreateBuilder(args);

// --- Configuração da Conexão com o Banco de Dados ---
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ??
                       throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

// --- Configuração do Identity ---
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

// --- Logging ---
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();
builder.Logging.SetMinimumLevel(LogLevel.Debug);

// --- Injeção de Dependência de Serviços ---
builder.Services.AddSingleton<ProfessorCourseMappingService>();

// HttpClient para serviços que usam base URL
builder.Services.AddHttpClient<IProfessorDashboardService, ProfessorDashboardService>(client =>
{
    var pythonApiBaseUrl = builder.Configuration["PythonApiBaseUrl"];
    if (string.IsNullOrEmpty(pythonApiBaseUrl))
    {
        client.BaseAddress = new Uri("http://127.0.0.1:5000/api/");
        builder.Logging.Services.BuildServiceProvider().GetRequiredService<ILogger<Program>>()
            .LogError("PythonApiBaseUrl não configurada. Usando fallback: http://127.0.0.1:5000/api/");
    }
    else
    {
        client.BaseAddress = new Uri(pythonApiBaseUrl);
        builder.Logging.Services.BuildServiceProvider().GetRequiredService<ILogger<Program>>()
            .LogInformation($"HttpClient para IProfessorDashboardService configurado com BaseAddress: {pythonApiBaseUrl}");
    }

    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// HttpClient genérico para controllers como RelatorioController
builder.Services.AddHttpClient();

// MVC e Razor
builder.Services.AddControllersWithViews();
builder.Services.AddRazorPages();

// --- Pipeline HTTP ---
var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();

// --- Rotas ---
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Account}/{action=Login}/{id?}");

app.MapRazorPages();
app.MapControllers();

app.Run();
