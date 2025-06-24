using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using IaPioniers.Models.Models_DB;
using IaPioniers.Models; // Certifique-se de que o namespace está correto

namespace IaPioniers.Data
{
    public class ApplicationDbContext : IdentityDbContext<ApplicationUser>
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        // Defina seus DbSet para cada modelo de entidade
        public DbSet<Professor> Professores { get; set; } = default!;
        public DbSet<Coordenador> Coordenadores { get; set; } = default!;
        public DbSet<Turma> Turmas { get; set; } = default!;
        public DbSet<Curso> Cursos { get; set; } = default!;
       

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

          
            builder.Entity<Professor>()
                .HasMany(p => p.Turmas) 
                .WithMany(t => t.Professores) 
                .UsingEntity(j => j.ToTable("ProfessorTurmas"));

          
            builder.Entity<Turma>()
                .HasOne(t => t.Curso)
                .WithMany(c => c.Turmas)
                .HasForeignKey(t => t.CursoId)
                .IsRequired(); 

           
            builder.Entity<Professor>()
                .HasOne(p => p.ApplicationUser)
                .WithOne(au => au.ProfessorProfile) 
                .HasForeignKey<Professor>(p => p.ApplicationUserId)
                .IsRequired(); 

            builder.Entity<Coordenador>()
                .HasOne(c => c.ApplicationUser)
                .WithOne(au => au.CoordenadorProfile) 
                .HasForeignKey<Coordenador>(c => c.ApplicationUserId)
                .IsRequired(); 
        }
    }
}