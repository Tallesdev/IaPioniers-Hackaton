using Microsoft.AspNetCore.Mvc;
using IaPioniers.Models; // Importe os modelos que você criou
using IaPioniers.Services; // Importe o namespace do seu serviço
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc.TagHelpers; // Para usar Task

namespace IaPioniers.Controllers
{
    [ApiController] // Indica que este controller serve APIs HTTP
    [Route("api/[controller]")] // Define a rota base como /api/CourseDetails
    public class CourseDetailsController : ControllerBase
    {
        private readonly IProfessorDashboardService _dashboardService;

        public CourseDetailsController(IProfessorDashboardService dashboardService)
        {
            _dashboardService = dashboardService;
        }

        // Endpoint para obter todos os detalhes e dados dos gráficos de uma turma específica
        // Este endpoint será chamado pelo JavaScript (frontend) da página de detalhes da turma.
        [HttpGet("{id}")] // Rota: /api/CourseDetails/{id} (ex: /api/CourseDetails/101)
        public async Task<ActionResult<CourseDetailedAnalystics>> GetCourseDetails(string id)
        {
            if (string.IsNullOrEmpty(id))
            {
                return BadRequest("O ID da turma é obrigatório.");
            }

            try
            {
                var detailedAnalystics = await _dashboardService.GetCourseDetailsAsync(id);

                if(detailedAnalystics == null)
                {
                    return NotFound($"Detalhes para a turma com ID'{id}' não encontrados.");
                }

                return Ok(detailedAnalystics);
            }
            catch(ApplicationException ex)
            {
                return StatusCode(500, $"Erro interno ao buscar detalhes da turma: {ex.Message}");
            }
            catch(Exception ex)
            {
                return StatusCode(500, $"Ocorreu um erro inesperado ao processar a requisição: {ex.Message}");
            }
        }
    }
}
