namespace IaPioniers.Models.Models_DB
{
    public class Curso
    {
        public int Id { get; set; }

        public string Nome { get; set; }
        public string Descricao { get; set; }


        public ICollection<Turma> Turmas { get; set; } = new List<Turma>();
    
}
}
