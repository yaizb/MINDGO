// --- Estado ---
let salaAbierta = true;
let participantes = [];
const maxParticipantes = 9;
let modoEliminacion = false;

// --- Elementos ---
const volumeBtn = document.getElementById('volumeBtn');
const volumeIcon = document.getElementById('volumeIcon');
const configBtn = document.getElementById('configBtn');
const configMenu = document.getElementById('configMenu');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const mainAudio = document.getElementById('mainAudio');

function generatePIN() {
    const num = Math.floor(100000 + Math.random() * 900000).toString();
    return num.substring(0, 3) + ' ' + num.substring(3);
}

// --- Inicializar ---
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('pinDisplay').textContent = generatePIN();
    // Simular que ya hay 9 participantes (como en el mockup)
    for (let i = 1; i <= 9; i++) {
        participantes.push(`Usuario ${String(i).padStart(2, '0')}`);
    }

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', (e) => {
        if (!configBtn.contains(e.target) && !configMenu.contains(e.target)) {
            configMenu.classList.remove('show');
        }
    });

    // Audio silenciado por defecto
    mainAudio.muted = true;
    updateVolumeIcon();
});

// --- Funciones ---

function removeRandomParticipant() {
    if (participantes.length === 0) return;
    const index = Math.floor(Math.random() * participantes.length);
    participantes.splice(index, 1);
    // Aquí podrías actualizar la UI si quisieras reducir el número
    configMenu.classList.remove('show');
    alert("Se eliminó un participante aleatoriamente.");
}

function updateVolumeIcon() {
    volumeIcon.className = mainAudio.muted
        ? 'bi bi-volume-mute-fill'
        : 'bi bi-volume-up-fill';
}

volumeBtn.addEventListener('click', () => {
    mainAudio.muted = !mainAudio.muted;
    updateVolumeIcon();
});

configBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    configMenu.classList.toggle('show');
});

fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.warn(`Error al entrar en pantalla completa: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
});
