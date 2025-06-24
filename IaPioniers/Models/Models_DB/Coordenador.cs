using System.ComponentModel.DataAnnotations;

namespace IaPioniers.Models.Models_DB
{
    public class Coordenador
    {
        public int Id { get; set; }
        [Required]
        public string Nome { get; set; }
        public string Email { get; set; } // Opcional

        // Chave estrangeira para ApplicationUser (um Coordenador é um ApplicationUser)
        public string ApplicationUserId { get; set; }
        public ApplicationUser ApplicationUser { get; set; }

    }
}
