using IaPioniers.Services;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using IaPioniers.Data;
using IaPioniers.Models;
using IaPioniers.Models.Models_DB;
using IaPioniers.Services;
using System.Net.Http; // Importe para HttpClient
using System;

var builder = WebApplication.CreateBuilder(args);


var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ??
                       throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

builder.Services.AddDefaultIdentity<ApplicationUser>(options =>
{
    // Configure suas opções de senha, bloqueio, etc. aqui.
    // Exemplo:
    options.SignIn.RequireConfirmedAccount = false; // Ajuste conforme sua necessidade
    options.Password.RequireDigit = false;
    options.Password.RequiredLength = 6;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase = false;
    options.Password.RequireLowercase = false;
})
.AddRoles<IdentityRole>() // Habilita o uso de Roles (como "Professor", "Coordenador")
.AddEntityFrameworkStores<ApplicationDbContext>();

builder.Services.AddHttpClient<IaPioniersApiService>(client =>
{
    // Use a URL base do appsettings.json, para flexibilidade
    client.BaseAddress = new Uri(builder.Configuration["PythonApiSettings:BaseUrl"] ?? "http://127.0.0.1:5000");

    // Adicione cabeçalhos padrão aqui se sua API Python precisar (ex: Accept, Auth, etc.)
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});
// Adicione aqui a configuração de logging
builder.Logging.ClearProviders(); // Limpa os provedores de log padrão
builder.Logging.AddConsole();    // Adiciona o provedor de log para o console
builder.Logging.AddDebug();      // Adiciona o provedor de log para a janela de Debug do VS

// Definir o nível mínimo de log para DEBUG para ver todas as mensagens
builder.Logging.SetMinimumLevel(LogLevel.Debug);

builder.Services.AddSingleton<ProfessorCourseMappingService>();

builder.Services.AddControllersWithViews(); 
builder.Services.AddRazorPages();

builder.Services.AddScoped<IProfessorDashboardService, ProfessorDashboardService>();


// Add services to the container.
builder.Services.AddControllersWithViews(); // Se estiver usando Views
builder.Services.AddControllers(); // Se for apenas uma API

builder.Services.AddScoped<IProfessorDashboardService, ProfessorDashboardService>();

builder.Services.AddHttpClient<IProfessorDashboardService, ProfessorDashboardService>(client =>
{

    client.BaseAddress = new Uri("http://127.0.0.1:5000"); // <--- MUDAR PARA A URL DA SUA API IA LOCAL

    // Você pode adicionar headers padrão se sua API IA precisar (ex: API Key)
    // client.DefaultRequestHeaders.Add("X-Api-Key", "sua_chave_secreta");
});


builder.Services.AddControllersWithViews();
builder.Services.AddRazorPages();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();

app.UseRouting();

app.UseAuthentication();

app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.MapControllers();

app.Run();
