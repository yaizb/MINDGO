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
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form[action="/registro"]');
  if (!form) return;

  form.querySelectorAll('input').forEach(input => {
    input.addEventListener('input', function () {
      let valido = true;

      if (this.name === "contrasena") {
        const pass = this.value;
        const tieneMayus = /[A-Z]/.test(pass);
        const tieneMinus = /[a-z]/.test(pass);
        const tieneNumero = /[0-9]/.test(pass);
        const tieneEspecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pass);
        valido = pass.length >= 8 && tieneMayus && tieneMinus && tieneNumero && tieneEspecial;
      } else if (this.type === "email") {
        valido = this.checkValidity() && this.value.includes("@");
      } else {
        valido = this.checkValidity();
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
});