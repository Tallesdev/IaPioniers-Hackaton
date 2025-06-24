namespace IaPioniers.Models.ViewModels
{
    public class DashboardViewModel
    {
        public string ProfessorNome { get; set; }
        public int TotalAlunos { get; set; }
        public int AlunosEmRisco { get; set; }
        public int NumeroAtividades { get; set; }
        public List<AtividadeModel> AtividadesRecentes { get; set; }
    }
}
