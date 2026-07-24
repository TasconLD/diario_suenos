// =============================================================
// 1. REGISTRO DE SERVICE WORKER Y PWA
// =============================================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => {
                console.log('PWA: Service Worker activo en', reg.scope);
                reg.update();
            })
            .catch(err => console.error('PWA: Error al registrar SW', err));
    });
}

// =============================================================
// 2. MODO OSCURO / CLARO
// =============================================================
const themeToggleBtn = document.getElementById('theme-toggle');
const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

function actualizarIconos() {
    if (document.documentElement.classList.contains('dark')) {
        if (themeToggleLightIcon) themeToggleLightIcon.classList.remove('hidden');
        if (themeToggleDarkIcon) themeToggleDarkIcon.classList.add('hidden');
    } else {
        if (themeToggleDarkIcon) themeToggleDarkIcon.classList.remove('hidden');
        if (themeToggleLightIcon) themeToggleLightIcon.classList.add('hidden');
    }
}

// Aplicar iconos al cargar
actualizarIconos();

if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function() {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        }
        actualizarIconos();
    });
}

// =============================================================
// 3. EVENTO DE INSTALACIÓN PWA
// =============================================================
let deferredPrompt;
const btnInstalar = document.getElementById('btn-instalar');
const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

window.addEventListener('beforeinstallprompt', (e) => {
    console.log('Evento beforeinstallprompt activado.');
    e.preventDefault();
    deferredPrompt = e;
    if (btnInstalar && !isStandalone) {
        btnInstalar.classList.remove('hidden');
    }
});

if (btnInstalar) {
    btnInstalar.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            console.log('PWA Outcome:', outcome);
            if (outcome === 'accepted') {
                btnInstalar.classList.add('hidden');
            }
            deferredPrompt = null;
        } else {
            alert('Para instalar en iPhone/iOS: Toca el icono de Compartir y luego "Añadir a la pantalla de inicio".');
        }
    });
}

window.addEventListener('appinstalled', () => {
    if (btnInstalar) {
        btnInstalar.classList.add('hidden');
    }
    deferredPrompt = null;
});

// =============================================================
// 4. MODAL DE EDICIÓN
// =============================================================
function abrirModalEdicion(boton) {
    const id = boton.getAttribute('data-id');
    const titulo = boton.getAttribute('data-titulo');
    const fecha = boton.getAttribute('data-fecha');
    const descripcion = boton.getAttribute('data-descripcion');
    const categoria = boton.getAttribute('data-categoria');
    const calidad = boton.getAttribute('data-calidad');
    const destacado = boton.getAttribute('data-destacado') === 'true';

    document.getElementById('form-edicion').action = '/editar/' + id;
    document.getElementById('edit-titulo').value = titulo;
    document.getElementById('edit-fecha').value = fecha;
    document.getElementById('edit-descripcion').value = descripcion;
    document.getElementById('edit-calidad').value = calidad;
    document.getElementById('edit-destacado').checked = destacado;
    
    if (categoria) {
        document.getElementById('edit-categoria').value = categoria;
    }
    document.getElementById('modal-edicion').classList.remove('hidden');
}