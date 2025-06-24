using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace IaPioniers.Models.Models_DB
{
    public class Professor
    {
        public int Id { get; set; }

        [Required]
        public string Nome { get; set; }

        public string Email { get; set; }


        public string ApplicationUserId { get; set; }
        public ApplicationUser ApplicationUser { get; set; }


        public ICollection<Turma> Turmas { get; set; } = new List<Turma>(); //tabela de junção entre Turma e Professor
    }
}
