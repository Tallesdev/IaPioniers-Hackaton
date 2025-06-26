namespace IaPioniers.Models.ViewModels
{
    public class TurmaCardViewModel 
    {
        public string TurmaNome { get; set; }
        public int QuantidadeAlunos { get; set; }
        // Se houver um ícone diferente para cada card de turma, adicione aqui (ex: string IconClass)
    }

    public class TurmasIndexViewModel
    {
        public string ProfessorNome { get; set; }
        public List<TurmaCardViewModel> Turmas { get; set; }
    }
}