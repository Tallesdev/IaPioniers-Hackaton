
﻿// Controllers/StudentController.cs
// Localização: IaPioniers/Controllers/StudentController.cs
using IaPioniers.Models; // Importa o namespace onde seu StudentSummary está
using IaPioniers.Models.ViewModels; // Garanta que este namespace está correto

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using Microsoft.EntityFrameworkCore.Metadata;
using System.Collections.Generic;

namespace IaPioniers.Controllers
{
    public class StudentController : Controller
    {
        public IActionResult Index()
        {
            var viewModel = new StudentViewModel
            {
                ProfessorNome = "Celso" // Nome do professor, como no protótipo
            };

            // Dados mockados dos alunos para a lista de cards (conforme image_4a4381.png)
            viewModel.Students.Add(new StudentSummary
            {
                userId = "1",
                userName = "Maria Eduarda",
                courseId = "A1",
                courseName = "Turma A",
                totalAccesses = 50,
                daysWithoutAcess = 2,
                evasionProbability = 0.1f,
                status = "Participando" // Conforme protótipo
                // Você pode adicionar uma propriedade "RecentDelivery" ou "AvatarUrl" aqui
                // ou gerá-los na View com base no status ou nome, se preferir não modificar o Model.
                // Por simplicidade, vou simular o "RecentDelivery" na View por enquanto.
            });
            viewModel.Students.Add(new StudentSummary
            {
                userId = "2",
                userName = "Talles Gabriel",
                courseId = "A1",
                courseName = "Turma A",
                totalAccesses = 10,
                daysWithoutAcess = 30,
                evasionProbability = 0.8f,
                status = "Inativo" // Conforme protótipo
            });
            viewModel.Students.Add(new StudentSummary
            {
                userId = "3",
                userName = "Geovana Fernandes",
                courseId = "A1",
                courseName = "Turma A",
                totalAccesses = 45,
                daysWithoutAcess = 7,
                evasionProbability = 0.3f,
                status = "Atrasado" // Conforme protótipo
            });
            viewModel.Students.Add(new StudentSummary
            {
                userId = "4",
                userName = "Gabrielly",
                courseId = "A1",
                courseName = "Turma A",
                totalAccesses = 5,
                daysWithoutAcess = 60,
                evasionProbability = 0.95f,
                status = "Inativo" // Conforme protótipo
            });

            // Dados mockados para o dropdown de turmas
            viewModel.AvailableClasses.Add("Turma A");
            viewModel.AvailableClasses.Add("Turma B");
            viewModel.AvailableClasses.Add("Turma C");

            viewModel.ClassesSelectList = new SelectList(viewModel.AvailableClasses);

            // Define a turma padrão selecionada (se houver uma)
            viewModel.SelectedClass = "Turma A"; // Por exemplo, "Turma A" será a padrão


            ViewData["Title"] = "Alunos";
            return View(viewModel); // Passa o ViewModel para a View
        }
    }
}
