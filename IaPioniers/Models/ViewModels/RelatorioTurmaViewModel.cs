using Microsoft.AspNetCore.Mvc.Rendering;
using System.Collections.Generic;

namespace IaPioniers.Models.ViewModels
{
    public class RelatorioTurmaViewModel
    {
        public int TurmaId {  get; set; }
        public List<SelectListItem> Turmas { get; set;} = new List<SelectListItem>();
    }
}
