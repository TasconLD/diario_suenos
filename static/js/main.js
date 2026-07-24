// Manejo del cambio de tema Claro / Oscuro
document.addEventListener("DOMContentLoaded", function () {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');

    function updateIcons() {
        if (document.documentElement.classList.contains('dark')) {
            darkIcon.classList.add('hidden');
            lightIcon.classList.remove('hidden');
        } else {
            lightIcon.classList.add('hidden');
            darkIcon.classList.remove('hidden');
        }
    }

    updateIcons();

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            document.documentElement.classList.toggle('dark');
            if (document.documentElement.classList.contains('dark')) {
                localStorage.setItem('theme', 'dark');
            } else {
                localStorage.setItem('theme', 'light');
            }
            updateIcons();
        });
    }
});

// Función para abrir el modal de edición y cargar la información del sueño
function abrirModalEdicion(btn) {
    const id = btn.getAttribute('data-id');
    const titulo = btn.getAttribute('data-titulo');
    const fecha = btn.getAttribute('data-fecha');
    const descripcion = btn.getAttribute('data-descripcion');
    const categoria = btn.getAttribute('data-categoria');
    const calidad = btn.getAttribute('data-calidad');
    const destacado = btn.getAttribute('data-destacado') === 'true';

    document.getElementById('form-edicion').action = '/editar/' + id;
    document.getElementById('edit-titulo').value = titulo;
    document.getElementById('edit-fecha').value = fecha;
    document.getElementById('edit-descripcion').value = descripcion;
    document.getElementById('edit-categoria').value = categoria;
    document.getElementById('edit-calidad').value = calidad;
    document.getElementById('edit-destacado').checked = destacado;

    document.getElementById('modal-edicion').classList.remove('hidden');
}