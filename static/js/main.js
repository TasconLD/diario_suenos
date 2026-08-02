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

// Lista de inputs que queremos rastrear
const camposEdicion = [
    'edit-titulo', 
    'edit-fecha', 
    'edit-descripcion', 
    'edit-categoria', 
    'edit-calidad'
];

function abrirModalEdicion(btn) {
    const id = btn.getAttribute('data-id');
    const titulo = btn.getAttribute('data-titulo');
    const fecha = btn.getAttribute('data-fecha');
    const descripcion = btn.getAttribute('data-descripcion');
    const categoria = btn.getAttribute('data-categoria');
    const calidad = btn.getAttribute('data-calidad');
    const destacado = btn.getAttribute('data-destacado') === 'true';

    const form = document.getElementById('form-edicion');
    if (form) form.action = '/editar/' + id;

    if (document.getElementById('edit-titulo')) document.getElementById('edit-titulo').value = titulo;
    if (document.getElementById('edit-fecha')) document.getElementById('edit-fecha').value = fecha;
    if (document.getElementById('edit-descripcion')) document.getElementById('edit-descripcion').value = descripcion;
    if (document.getElementById('edit-categoria')) document.getElementById('edit-categoria').value = categoria;
    if (document.getElementById('edit-calidad')) document.getElementById('edit-calidad').value = calidad;
    if (document.getElementById('edit-destacado')) document.getElementById('edit-destacado').checked = destacado;

    // --- Restaurar borrador de localStorage si existe ---
    const actionUrl = form ? form.action : '';
    if (actionUrl) {
        camposEdicion.forEach(fieldId => {
            const savedValue = localStorage.getItem(`draft_${actionUrl}_${fieldId}`);
            if (savedValue !== null) {
                const input = document.getElementById(fieldId);
                if (input) input.value = savedValue;
            }
        });
    }

    document.getElementById('modal-edicion').classList.remove('hidden');
}

// 2. SISTEMA DE AUTO-GUARDADO Y CONTROL DE SCROLL

document.addEventListener('DOMContentLoaded', () => {
    
    // A. RESTAURAR POSICIÓN DEL SCROLL TRAS GUARDAR (Evita que se mande arriba)
    const scrollPos = localStorage.getItem('scroll_pos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos, 10));
        localStorage.removeItem('scroll_pos'); 
    }

    // B. AUTO-GUARDADO MIENTRAS ESCRIBES
    camposEdicion.forEach(id => {
        const elem = document.getElementById(id);
        if (elem) {
            elem.addEventListener('input', () => {
                const formAction = document.getElementById('form-edicion')?.action;
                if (formAction) {
                    localStorage.setItem(`draft_${formAction}_${id}`, elem.value);
                }
            });
        }
    });

    // C. MANEJAR EL ENVÍO DEL FORMULARIO DE EDICIÓN
    const formEdicion = document.getElementById('form-edicion');
    if (formEdicion) {
        formEdicion.addEventListener('submit', () => {
            // 1. Guardar la altura exacta donde estaba el usuario antes de procesar el POST
            localStorage.setItem('scroll_pos', window.scrollY);

            // 2. Limpiar borradores
            const formAction = formEdicion.action;
            camposEdicion.forEach(id => {
                localStorage.removeItem(`draft_${formAction}_${id}`);
            });
        });
    }
});