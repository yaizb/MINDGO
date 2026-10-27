// Cambiar entre vistas del ranking
document.querySelectorAll('.tab-btn').forEach(button => {
    button.addEventListener('click', () => {
        // Remover active de todos los botones
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        // Agregar active al botón clickeado
        button.classList.add('active');

        // Ocultar todas las vistas
        document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
        // Mostrar la vista correspondiente
        const tabId = button.getAttribute('data-tab');
        document.getElementById(`view-${tabId}`).classList.add('active');
    });
});
