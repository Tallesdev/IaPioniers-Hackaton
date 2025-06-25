
﻿// Controllers/StudentController.cs (ou AlunoController.cs)

using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic; // Para usar List<string> ou uma lista de objetos Aluno
// using Atena.Models; // Descomente se você já tiver um modelo Aluno

public class StudentController : Controller
{
    // Ação para exibir a lista de alunos
    public IActionResult Index()
    {
        ViewData["Title"] = "Alunos"; // Define o título da página

        // Aqui você buscaria seus alunos do banco de dados.
        // Por enquanto, vamos usar uma lista mock para simular dados.
        var students = new List<string>
        {
            "Ana Silva",
            "Bruno Mendes",
            "Carla Costa",
            "Daniel Pereira",
            "Mariana Almeida"
        };

        // Você passaria um modelo mais complexo para a View no futuro,
        // por exemplo, List<AlunoModel>
        return View(students);
    }

    // Ação para exibir o formulário de adição de aluno
    public IActionResult Add()
    {
        ViewData["Title"] = "Adicionar Novo Aluno";
        return View();
    }

    // Ação para lidar com o POST do formulário de adição
    [HttpPost]
    public IActionResult Add(string studentName) // Substitua 'string studentName' pelo seu modelo Aluno
    {
        // Lógica para adicionar o aluno ao banco de dados
        // Console.WriteLine($"Adicionando aluno: {studentName}");

        // Redireciona de volta para a lista de alunos
        return RedirectToAction("Index");
    }
}

    // Ações para Editar, Detalhes, Excluir viriam aqui...
    // public IActionResult Edit(int id) { ... }
    // public IActionResult Details(int id) { ... }
    // public IActionResult Delete(int id) { ... }
