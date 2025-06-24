using Microsoft.AspNetCore.Identity;
using IaPioniers.Models.Models_DB;

namespace IaPioniers.Models
{
    public class ApplicationUser : IdentityUser
    {
        public string NomeCompleto { get; set; }

        public Professor? ProfessorProfile { get; set; }
        public Coordenador? CoordenadorProfile { get; set; }

    }
}
