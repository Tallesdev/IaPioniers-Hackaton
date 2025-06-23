using IaPioniers.Services;
using System.Net.Http; // Importe para HttpClient
using System;

var builder = WebApplication.CreateBuilder(args);

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

app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.MapControllers();

app.Run();
