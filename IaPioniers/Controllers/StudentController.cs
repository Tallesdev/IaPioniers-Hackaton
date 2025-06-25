// Controllers/StudentController.cs
using Microsoft.AspNetCore.Mvc;
using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;
using IaPioniers.Models; // Para desserializar JSON
// ... outros using

public class StudentController : Controller
{
    private readonly HttpClient _httpClient; // HttpClient para chamar a API Flask

    public StudentController(HttpClient httpClient)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri("https://localhost:7053/api/"); // Base da sua API Flask
    }

    [HttpGet("PerfilAluno/{userId}")] // Rota para esta ação
    public async Task<IActionResult> PerfilAluno(string userId)
    {
        try
        {
            // Chama o endpoint da sua API Flask
            HttpResponseMessage response = await _httpClient.GetAsync($"student/student-profile/{userId}");

            if (response.IsSuccessStatusCode)
            {
                string jsonResponse = await response.Content.ReadAsStringAsync();
                // Supondo que você tenha uma classe modelo para os dados do aluno
                var studentProfile = JsonConvert.DeserializeObject<StudentProfile>(jsonResponse);
                return View(studentProfile); // Passa o modelo para a view PerfilAluno.cshtml
            }
            else
            {
                // Lidar com erros da API Flask
                return View("Error"); // Ou passar uma mensagem de erro para a view
            }
        }
        catch (Exception ex)
        {
            // Lidar com erros de rede, etc.
            return View("Error");
        }
    }
}