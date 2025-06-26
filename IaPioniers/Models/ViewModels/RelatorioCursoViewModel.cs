using Microsoft.AspNetCore.Mvc.Rendering;

namespace IaPioniers.Models.ViewModels
{
    public class RelatorioCursoViewModel
    {
        public string CursoSelecionado { get; set; }
        public List<SelectListItem> Cursos { get; set; } = new();
    }
}
