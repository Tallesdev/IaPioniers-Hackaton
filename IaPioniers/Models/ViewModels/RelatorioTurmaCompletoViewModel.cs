using Microsoft.AspNetCore.Mvc.Rendering;
using IaPioniers.Models.Models_DB;


namespace IaPioniers.Models.ViewModels
{
    public class RelatorioTurmaCompletoViewModel
    {
        public Turma Turma { get; set; }
    public List<IAAlunoEvasao> AlunosEmRisco { get; set; } = new();
    }
}
