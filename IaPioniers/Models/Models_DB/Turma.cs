namespace IaPioniers.Models.Models_DB
{
    public class Turma
    {
        public int TurmaId { get; set; }

        public string Codigo { get; set; }
        public int AnoLetivo { get; set; }


        public int CursoId { get; set; }
        public Curso Curso { get; set; }


        public ICollection<Professor> Professores { get; set; } = new List<Professor>();
    
}
}
