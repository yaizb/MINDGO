const leftBtn = document.querySelector(".arrow.left");
const rightBtn = document.querySelector(".arrow.right");
const container = document.querySelector(".carousel-container");

leftBtn.addEventListener("click", () => {
  container.scrollBy({ left: -200, behavior: "smooth" });
});

rightBtn.addEventListener("click", () => {
  container.scrollBy({ left: 200, behavior: "smooth" });
});

// Validación de formulario en tiempo real
document.querySelectorAll('#registroForm input').forEach(input => {
  input.addEventListener('input', function() {
    let valido = this.checkValidity();

    // Validación personalizada para contraseña
    if (this.name === "contrasena") {
      valido = valido && this.value.length >= 8;
    }

    // Validación personalizada para email
    if (this.name === "email") {
      valido = valido && this.value.includes("@");
    }

    if (valido) {
      this.classList.add('valid');
      this.classList.remove('invalid');
    } else {
      this.classList.add('invalid');
      this.classList.remove('valid');
    }
  });
});