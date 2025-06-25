using Microsoft.AspNetCore.Mvc.Rendering;

namespace IaPioniers.Models.ViewModels
{
    public class StudentViewModel
    {
        public string ProfessorNome { get; set; }
        public List<StudentSummary> Students { get; set; } // Usa seu StudentSummary existente
        public List<string> AvailableClasses { get; set; }

        public string SelectedClass { get; set; }
        public SelectList ClassesSelectList { get; set; }

        public StudentViewModel()
        {
            Students = new List<StudentSummary>();
            AvailableClasses = new List<string>();
            // Inicialização padrão, pode ser sobrescrita no Controller
            ClassesSelectList = new SelectList(new List<string>());
        }
    }
}
