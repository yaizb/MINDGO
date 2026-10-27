// ===== BIBLIOTECA DE CUESTIONARIOS =====

let cuestionarios = [];
let seccionActual = 'cuestionarios'; // 'favoritos', 'cuestionarios', 'papelera'

// Cargar cuestionarios al iniciar
document.addEventListener('DOMContentLoaded', function() {
  cargarCuestionarios();
  configurarEventos();
});

// ===== CARGAR CUESTIONARIOS DEL USUARIO =====
async function cargarCuestionarios() {
  try {
    const response = await fetch('/biblioteca/mis-cuestionarios');
    const data = await response.json();

    if (data.success) {
      cuestionarios = data.cuestionarios;
      renderizarCuestionarios();
    }
  } catch (error) {
    console.error('Error al cargar cuestionarios:', error);
    mostrarMensaje('Error al cargar cuestionarios', 'error');
  }
}

// ===== RENDERIZAR CUESTIONARIOS EN EL GRID =====
function renderizarCuestionarios() {
  const grid = document.getElementById('cuestionariosGrid');

  // Filtrar según sección actual
  let cuestionariosFiltrados = [];

  switch(seccionActual) {
    case 'favoritos':
      cuestionariosFiltrados = cuestionarios.filter(c => c.es_favorito && !c.en_papelera);
      break;
    case 'papelera':
      cuestionariosFiltrados = cuestionarios.filter(c => c.en_papelera);
      break;
    case 'completado':
      // Filtrar cuestionarios que tienen sesiones finalizadas
      cuestionariosFiltrados = cuestionarios.filter(c => 
        !c.en_papelera && c.num_completados > 0
      );
      // Ordenar por última vez jugado (más reciente primero)
      cuestionariosFiltrados.sort((a, b) => {
        if (!a.ultima_vez_jugado) return 1;
        if (!b.ultima_vez_jugado) return -1;
        return new Date(b.ultima_vez_jugado) - new Date(a.ultima_vez_jugado);
      });
      break;
    default: // 'cuestionarios'
      cuestionariosFiltrados = cuestionarios.filter(c => !c.en_papelera);
      // Ordenar: favoritos primero, luego por fecha
      cuestionariosFiltrados.sort((a, b) => {
        if (a.es_favorito && !b.es_favorito) return -1;
        if (!a.es_favorito && b.es_favorito) return 1;
        return 0; // Mantener orden original por fecha
      });
  }

  if (cuestionariosFiltrados.length === 0) {
    const mensajes = {
      'favoritos': 'No tienes cuestionarios favoritos aún.',
      'papelera': 'La papelera está vacía.',
      'completado': 'No tienes cuestionarios completados aún.',
      'cuestionarios': 'No tienes cuestionarios aún.'
    };

    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
        <i class="bi bi-journal-plus" style="font-size: 4rem; color: #ccc;"></i>
        <p style="color: #999; font-size: 1.2rem; margin-top: 20px;">
          ${mensajes[seccionActual]} <br>
          ${seccionActual === 'cuestionarios' ? '<a href="/cuestionario" style="color: #e94e77; text-decoration: underline;">Crea tu primer cuestionario</a>' : ''}
        </p>
      </div>
    `;
    return;
  }

  grid.innerHTML = '';

  // Si estamos en papelera, agregar botón "Limpiar todo" al inicio
  if (seccionActual === 'papelera' && cuestionariosFiltrados.length > 0) {
    const botonLimpiar = document.createElement('div');
    botonLimpiar.style.cssText = 'grid-column: 1 / -1; text-align: right; margin-bottom: 15px;';
    botonLimpiar.innerHTML = `
      <button onclick="limpiarPapeleraCompleta()" style="
        background: #e94e77;
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 25px;
        font-weight: 600;
        font-family: 'Fredoka', sans-serif;
        cursor: pointer;
        box-shadow: 0 3px 10px rgba(233, 78, 119, 0.4);
        transition: all 0.3s ease;
      " onmouseover="this.style.background='#d43964'" onmouseout="this.style.background='#e94e77'">
        <i class="bi bi-trash3"></i> Limpiar todo
      </button>
    `;
    grid.appendChild(botonLimpiar);
  }

  cuestionariosFiltrados.forEach(cuestionario => {
    const card = crearCardCuestionario(cuestionario);
    grid.appendChild(card);
  });
}

// ===== CREAR CARD DE CUESTIONARIO =====
function crearCardCuestionario(cuestionario) {
  const card = document.createElement('div');
  card.className = 'cuestionario-card-outer'; // Card exterior rosa
  card.dataset.id = cuestionario.id;

  const esFavorito = cuestionario.es_favorito || false;
  const numPreguntas = cuestionario.num_preguntas || 0;
  const enPapelera = cuestionario.en_papelera || false;
  const descripcion = cuestionario.descripcion || '';

  card.innerHTML = `
    <!-- Corazón de favorito en la esquina superior izquierda -->
    ${!enPapelera ? `
      <button class="btn-favorito ${esFavorito ? 'active' : ''}" onclick="toggleFavorito(${cuestionario.id})">
        <i class="bi ${esFavorito ? 'bi-heart-fill' : 'bi-heart'}"></i>
      </button>
    ` : ''}

    <!-- Card interior blanco con todo el contenido -->
    <div class="cuestionario-card-inner">
      <!-- Imagen de preview -->
      <div class="card-preview" ${!enPapelera ? `onclick="ingresarCuestionario(${cuestionario.id})"` : ''}>
        ${!enPapelera ? `
          <div class="preview-overlay">
            <button class="btn-ver-cuestionario" onclick="event.stopPropagation(); ingresarCuestionario(${cuestionario.id})">
              <i class="bi bi-eye"></i>
            </button>
          </div>
        ` : ''}
        <div class="card-preview-content">
          <i class="bi bi-file-earmark-text" style="font-size: 3.5rem; color: #ccc;"></i>
          <p style="margin-top: 12px; color: #aaa; font-size: 1rem;">
            ${numPreguntas} pregunta${numPreguntas !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      <!-- Sección inferior con fondo rosa -->
      <div class="card-footer-section">
        <!-- Título -->
        <div class="card-titulo-container">
          <h3 class="card-titulo">${cuestionario.titulo || 'Sin título'}</h3>
        </div>

        <!-- Descripción -->
        ${descripcion ? `<p class="card-descripcion">${descripcion}</p>` : ''}

        <!-- Botones de acción -->
        <div class="card-actions">
          ${!enPapelera ? `
            <button class="btn-editar" onclick="editarCuestionario(${cuestionario.id})">Editar</button>
            <button class="btn-eliminar" onclick="confirmarEliminar(${cuestionario.id})">
              <i class="bi bi-trash"></i>
            </button>
          ` : `
            <button class="btn-restaurar" onclick="restaurarCuestionario(${cuestionario.id})">
              <i class="bi bi-arrow-counterclockwise"></i> Restaurar
            </button>
            <button class="btn-eliminar-permanente" onclick="confirmarEliminarPermanente(${cuestionario.id})">
              <i class="bi bi-trash-fill"></i> Eliminar
            </button>
          `}
        </div>
      </div>
    </div>
  `;

  return card;
}

// ===== INGRESAR AL CUESTIONARIO (MODO JUEGO) =====
let cuestionarioIdSeleccionado = null;

function ingresarCuestionario(id) {
  cuestionarioIdSeleccionado = id;
  const modal = document.getElementById('modalModoJuego');
  modal.style.display = 'flex';

  // Asegurar que las opciones grupales estén ocultas al abrir
  document.getElementById('opcionesGrupal').style.display = 'none';
  document.querySelector('input[name="modoJuego"][value="individual"]').checked = true;

  // Escuchar cambios en el modo
  const modoInputs = document.querySelectorAll('input[name="modoJuego"]');
  modoInputs.forEach(input => {
    input.addEventListener('change', function() {
      document.getElementById('opcionesGrupal').style.display =
        this.value === 'grupal' ? 'block' : 'none';
    });
  });
}

function cerrarModalModoJuego() {
  document.getElementById('modalModoJuego').style.display = 'none';
  cuestionarioIdSeleccionado = null;
}

function confirmarModoJuego() {
  if (!cuestionarioIdSeleccionado) return;

  const modo = document.querySelector('input[name="modoJuego"]:checked').value;
  let url = `/salaEspera?id=${cuestionarioIdSeleccionado}&modo=${modo}`;

  if (modo === 'grupal') {
    const numGrupos = parseInt(document.getElementById('numGrupos').value);
    const maxIntegrantes = parseInt(document.getElementById('maxIntegrantes').value);

    if (isNaN(numGrupos) || isNaN(maxIntegrantes) || numGrupos < 2 || maxIntegrantes < 2) {
      alert('Por favor, ingresa valores válidos (mínimo 2 para grupos e integrantes).');
      return;
    }

    url += `&grupos=${numGrupos}&maxIntegrantes=${maxIntegrantes}`;
  }

  cerrarModalModoJuego();
  window.location.href = url;
}

// ===== EDITAR CUESTIONARIO =====
function editarCuestionario(id) {
  window.location.href = `/cuestionario?id=${id}`;
}

// ===== TOGGLE FAVORITO =====
async function toggleFavorito(id) {
  try {
    const response = await fetch(`/biblioteca/favorito/${id}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      // Actualizar estado local
      const cuestionario = cuestionarios.find(c => c.id === id);
      if (cuestionario) {
        cuestionario.es_favorito = data.es_favorito;
      }

      // Re-renderizar
      renderizarCuestionarios();

      const mensaje = data.es_favorito ? 'Añadido a favoritos' : 'Eliminado de favoritos';
      mostrarMensaje(mensaje, 'success');
    }
  } catch (error) {
    console.error('Error al actualizar favorito:', error);
    mostrarMensaje('Error al actualizar favorito', 'error');
  }
}

// ===== CONFIRMAR ELIMINAR =====
function confirmarEliminar(id) {
  const cuestionario = cuestionarios.find(c => c.id === id);
  const titulo = cuestionario ? cuestionario.titulo : 'este cuestionario';

  if (confirm(`¿Mover "${titulo}" a la papelera?`)) {
    moverAPapelera(id);
  }
}

// ===== MOVER A PAPELERA =====
async function moverAPapelera(id) {
  try {
    const response = await fetch(`/biblioteca/papelera/${id}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      // Actualizar estado local
      const cuestionario = cuestionarios.find(c => c.id === id);
      if (cuestionario) {
        cuestionario.en_papelera = true;
      }

      renderizarCuestionarios();
      mostrarMensaje('Cuestionario movido a la papelera', 'success');
    } else {
      mostrarMensaje('Error al mover a papelera', 'error');
    }
  } catch (error) {
    console.error('Error al mover a papelera:', error);
    mostrarMensaje('Error al mover a papelera', 'error');
  }
}

// ===== RESTAURAR CUESTIONARIO =====
async function restaurarCuestionario(id) {
  try {
    const response = await fetch(`/biblioteca/restaurar/${id}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      // Actualizar estado local
      const cuestionario = cuestionarios.find(c => c.id === id);
      if (cuestionario) {
        cuestionario.en_papelera = false;
      }

      renderizarCuestionarios();
      mostrarMensaje('Cuestionario restaurado', 'success');
    } else {
      mostrarMensaje('Error al restaurar', 'error');
    }
  } catch (error) {
    console.error('Error al restaurar:', error);
    mostrarMensaje('Error al restaurar', 'error');
  }
}

// ===== CONFIRMAR ELIMINAR PERMANENTE =====
function confirmarEliminarPermanente(id) {
  const cuestionario = cuestionarios.find(c => c.id === id);
  const titulo = cuestionario ? cuestionario.titulo : 'este cuestionario';

  if (confirm(`¿Eliminar permanentemente "${titulo}"? Esta acción no se puede deshacer.`)) {
    eliminarCuestionario(id);
  }
}

// ===== ELIMINAR CUESTIONARIO =====
async function eliminarCuestionario(id) {
  try {
    const response = await fetch(`/biblioteca/eliminar/${id}`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (data.success) {
      // Eliminar del array local
      cuestionarios = cuestionarios.filter(c => c.id !== id);

      // Re-renderizar
      renderizarCuestionarios();

      mostrarMensaje('Cuestionario eliminado', 'success');
    }
  } catch (error) {
    console.error('Error al eliminar cuestionario:', error);
    mostrarMensaje('Error al eliminar cuestionario', 'error');
  }
}

// ===== LIMPIAR PAPELERA COMPLETA =====
async function limpiarPapeleraCompleta() {
  const cuestionariosEnPapelera = cuestionarios.filter(c => c.en_papelera);

  if (cuestionariosEnPapelera.length === 0) {
    mostrarMensaje('La papelera ya está vacía', 'info');
    return;
  }

  const confirmar = confirm(`¿Eliminar permanentemente los ${cuestionariosEnPapelera.length} cuestionario(s) en papelera?\n\nEsta acción no se puede deshacer.`);

  if (!confirmar) return;

  try {
    const response = await fetch('/biblioteca/limpiar-papelera', {
      method: 'DELETE'
    });

    const data = await response.json();

    if (data.success) {
      // Eliminar todos los cuestionarios en papelera del array local
      cuestionarios = cuestionarios.filter(c => !c.en_papelera);

      // Re-renderizar
      renderizarCuestionarios();

      mostrarMensaje(`${data.eliminados} cuestionario(s) eliminado(s) permanentemente`, 'success');
    } else {
      mostrarMensaje('Error al limpiar papelera', 'error');
    }
  } catch (error) {
    console.error('Error al limpiar papelera:', error);
    mostrarMensaje('Error al limpiar papelera', 'error');
  }
}

// ===== CONFIGURAR EVENTOS =====
function configurarEventos() {
  // Navegación del sidebar
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', function(e) {
      e.preventDefault();

      // Remover active de todos
      navItems.forEach(nav => nav.classList.remove('active'));

      // Agregar active al clickeado
      this.classList.add('active');

      // Obtener sección desde el atributo data-seccion
      const seccion = this.getAttribute('data-seccion');
      cambiarSeccion(seccion);
    });
  });
}

// ===== CAMBIAR SECCIÓN =====
function cambiarSeccion(seccion) {
  seccionActual = seccion;

  // Actualizar título
  const titulo = {
    'favoritos': 'Favoritos',
    'papelera': 'Papelera',
    'completado': 'Completado',
    'cuestionarios': 'Cuestionarios'
  };

  const seccionTitulo = document.querySelector('.seccion-titulo');
  if (seccionTitulo) {
    seccionTitulo.textContent = titulo[seccion] || 'Cuestionarios';
  }

  // Re-renderizar
  renderizarCuestionarios();
}

// ===== UTILIDADES =====
function mostrarMensaje(texto, tipo = 'info') {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    background: ${tipo === 'success' ? '#4CAF50' : tipo === 'error' ? '#f44336' : tipo === 'warning' ? '#ff9800' : '#2196F3'};
    color: white;
    padding: 15px 25px;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    z-index: 10000;
    font-weight: 600;
    animation: slideIn 0.3s ease;
  `;
  toast.textContent = texto;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
