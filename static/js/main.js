// static/js/main.js

// ==========================================
// 1. MANEJO DEL TEMA CLARO / OSCURO
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');

    function updateIcons() {
        if (!darkIcon || !lightIcon) return;
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


// ==========================================
// 2. EDICIÓN DE SUEÑOS Y AUTO-GUARDADO
// ==========================================
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

    // Restaurar borrador de localStorage si existe
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

    const modalEdicion = document.getElementById('modal-edicion');
    if (modalEdicion) modalEdicion.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    // Restaurar posición del scroll tras guardar
    const scrollPos = localStorage.getItem('scroll_pos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos, 10));
        localStorage.removeItem('scroll_pos'); 
    }

    // Auto-guardado mientras escribes
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

    // Envío del formulario de edición
    const formEdicion = document.getElementById('form-edicion');
    if (formEdicion) {
        formEdicion.addEventListener('submit', () => {
            localStorage.setItem('scroll_pos', window.scrollY);
            const formAction = formEdicion.action;
            camposEdicion.forEach(id => {
                localStorage.removeItem(`draft_${formAction}_${id}`);
            });
        });
    }
});


// ==========================================
// 3. SEGURIDAD Y AJUSTES DE CUENTA
// ==========================================

// Alternar visibilidad de la contraseña
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');

    if (!input || !icon) return;

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Abrir y Cerrar Modal de Seguridad / Ajustes
function abrirModalSeguridad() {
    const modal = document.getElementById('modal-cambiar-pass');
    if (modal) modal.classList.remove('hidden');
}

function cerrarModalSeguridad() {
    const modal = document.getElementById('modal-cambiar-pass');
    if (modal) modal.classList.add('hidden');
    
    const errorElem = document.getElementById('msg-error-pass');
    if (errorElem) errorElem.classList.add('hidden');
}

// Validación de coincidencia de nuevas contraseñas
function validarContrasenas(event) {
    const passNuevaInput = document.getElementById('pass-nueva');
    const passConfirmarInput = document.getElementById('pass-confirmar');
    const errorElem = document.getElementById('msg-error-pass');

    if (!passNuevaInput || !passConfirmarInput) return true;

    const passNueva = passNuevaInput.value;
    const passConfirmar = passConfirmarInput.value;

    if (passNueva !== passConfirmar) {
        if (event) event.preventDefault();
        if (errorElem) {
            errorElem.textContent = 'Las nuevas contraseñas no coinciden.';
            errorElem.classList.remove('hidden');
        } else {
            alert('Las nuevas contraseñas no coinciden.');
        }
        return false;
    }
    
    if (errorElem) errorElem.classList.add('hidden');
    return true;
}

// Cerrar modal al presionar la tecla ESC
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        cerrarModalSeguridad();
    }
});