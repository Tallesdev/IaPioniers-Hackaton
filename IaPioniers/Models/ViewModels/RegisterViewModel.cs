using System.ComponentModel.DataAnnotations;

namespace IaPioniers.Models.ViewModels
{
    public class RegisterViewModel
    {
        [Required]
        public string NomeCompleto { get; set; }

        [Required]
        [EmailAddress]
        public string Email { get; set; }

        [Required]
        [DataType(DataType.Password)]
        public string Senha { get; set; }

        [Required]
        [DataType(DataType.Password)]
        [Compare("Senha", ErrorMessage = "A senha e a confirmação devem ser iguais.")]
        public string ConfirmarSenha { get; set; }
    }
}
