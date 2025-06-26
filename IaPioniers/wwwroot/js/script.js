document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    // mainContent não é estritamente necessário para o toggle de largura com flexbox
    // const mainContent = document.getElementById('main-content'); 

    if (sidebar && sidebarToggleBtn) { // Verifica se os elementos existem
        sidebarToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('closed');
            // Se você quiser que o ícone do botão mude (ex: hambúrguer para X ou seta)
            const icon = sidebarToggleBtn.querySelector('i');
            if (icon) {
                if (sidebar.classList.contains('closed')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-arrow-right'); // Ou fa-chevron-right, fa-times, etc.
                } else {
                    icon.classList.remove('fa-arrow-right');
                    icon.classList.add('fa-bars');
                }
            }
        });
    }

    // Opcional: Adicionar funcionalidade para fechar o sidebar em telas menores ao clicar fora
    // ou ao redimensionar a janela.
});


document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebarToggle');

    if (sidebar && sidebarToggleBtn) { // Verifica se os elementos existem
        sidebarToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('closed');

            // Lógica para mudar o ícone do botão (opcional)
            const icon = sidebarToggleBtn.querySelector('i');
            if (icon) {
                if (sidebar.classList.contains('closed')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-chevron-right'); // Ícone de seta para a direita quando fechado
                } else {
                    icon.classList.remove('fa-chevron-right');
                    icon.classList.add('fa-bars'); // Ícone de hambúrguer quando aberto
                }
            }
        });
    }
});