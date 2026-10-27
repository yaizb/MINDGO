document.addEventListener("DOMContentLoaded", () => {
  const lista = document.getElementById("listaPreguntas");
  const modal = document.querySelector(".modal-cuestionario-overlay");
  const btnPublicar = document.getElementById("btnPublicar");
  const btnCerrar = document.getElementById("btnCerrarModal");
  const btnConfirmar = document.getElementById("btnConfirmarPublicar");
  const btnMasRespuestas = document.getElementById("btnMasRespuestas");
  const btnNuevaPregunta = document.getElementById("btnNuevaPregunta");
  const respuestasContainer = document.getElementById("respuestasContainer");
  const inputPregunta = document.getElementById("inputPregunta");
  const imagenInput = document.getElementById("imagenInput");
  const previewImg = document.getElementById("previewImg");
  const previewContainer = document.getElementById("previewContainer");
  const uploadArea = document.querySelector(".upload-area");

  // Panel derecho
  const tipoSel = document.getElementById("tipoPregunta");
  const comboCorrecta = document.getElementById("opcionCorrecta");
  const labelCorrecta = comboCorrecta ? comboCorrecta.previousElementSibling : null;

  // Botones duplicar/eliminar de la pregunta actual
  const btnDuplicar = document.getElementById("btnDuplicar");
  const btnEliminar = document.getElementById("btnEliminar");

  // Detectar edición
  const params = new URLSearchParams(location.search);
  let idCuestionario = params.get('id') ? parseInt(params.get('id')) : null;

  // Cambiar texto del botón si estamos editando
  if (idCuestionario) {
    if (btnConfirmar) btnConfirmar.textContent = "Guardar cambios";
  }

  let preguntas = [];
  let preguntaActual = 0;

  inicializar();

  async function inicializar() {
    await cargarConfiguraciones();
    if (idCuestionario) {
      await cargarCuestionarioExistente(idCuestionario);
    } else {
      agregarPregunta();
    }
    actualizarModal(false);
  }

  // =============================
  //      CONFIGURACIONES
  // =============================
  async function cargarConfiguraciones() {
    const tiempoSel = document.getElementById("limiteTiempo");
    const puntajeSel = document.getElementById("tipoPuntaje");

    try {
      const res = await fetch("/tipos-pregunta");
      const tipos = await res.json();
      tipoSel.innerHTML = tipos.map(t => `<option value="${t}">${t}</option>`).join("");
    } catch {
      tipoSel.innerHTML = `
        <option>Selección Simple</option>
        <option>Selección Múltiple</option>
        <option>Verdadero/Falso</option>
        <option>Abierta</option>
      `;
    }

    const tiempos = [5, 10, 20, 30, 45, 60];
    tiempoSel.innerHTML = tiempos.map(t => `<option>${t} seg</option>`).join("");

    const puntajes = ["Puntuación simple", "Por rapidez", "Sin puntaje"];
    puntajeSel.innerHTML = puntajes.map(p => `<option>${p}</option>`).join("");
  }

  function mostrarComboCorrecta(visible) {
    if (!comboCorrecta) return;
    comboCorrecta.style.display = visible ? "block" : "none";
    if (labelCorrecta) labelCorrecta.style.display = visible ? "block" : "none";
  }

  // Texto de respuesta correcta para preguntas abiertas
  function renderCampoAbiertaPanel(p) {
    const ya = document.getElementById("inputCorrectaAbierta");
    if (ya) ya.remove();

    if (p.tipo !== "Abierta") return;
    if (!comboCorrecta || !comboCorrecta.parentNode) return;

    const input = document.createElement("input");
    input.id = "inputCorrectaAbierta";
    input.type = "text";
    input.placeholder = "Escribe la respuesta correcta…";
    input.className = "input-opcion";
    input.style.marginTop = "8px";
    input.value = (p.opciones[0]?.texto ?? "");

    comboCorrecta.parentNode.insertBefore(input, comboCorrecta.nextSibling);

    input.addEventListener("input", (e) => {
      if (!p.opciones.length) p.opciones.push({ texto: "", es_correcta: true });
      p.opciones[0].texto = e.target.value;
      renderPreguntas();
    });
  }

  // =============================
  //      CREAR PREGUNTA
  // =============================
  function nuevaEstructuraOpciones(tipo) {
    if (tipo === "Verdadero/Falso") {
      return [
        { texto: "Verdadero", es_correcta: false },
        { texto: "Falso", es_correcta: false }
      ];
    }
    if (tipo === "Abierta") {
      return [{ texto: "", es_correcta: true }];
    }
    return [
      { texto: "Opción 1", es_correcta: false },
      { texto: "Opción 2", es_correcta: false },
      { texto: "Opción 3", es_correcta: false },
      { texto: "Opción 4", es_correcta: false }
    ];
  }

  function agregarPregunta() {
    const tipoInicial = "Selección Simple";
    preguntas.push({
      texto: `Pregunta ${preguntas.length + 1}`,
      tipo: tipoInicial,
      opciones: nuevaEstructuraOpciones(tipoInicial),
      imagen: ""
    });
    renderPreguntas();
    mostrarPregunta(preguntas.length - 1);
  }

  btnNuevaPregunta.onclick = () => agregarPregunta();

  // duplicar actual
  btnDuplicar.onclick = () => {
    const clon = JSON.parse(JSON.stringify(preguntas[preguntaActual]));
    clon.texto = `Pregunta ${preguntas.length + 1}`;
    preguntas.push(clon);
    renderPreguntas();
    mostrarPregunta(preguntas.length - 1);
  };

  // eliminar actual
  btnEliminar.onclick = () => {
    if (preguntas.length === 1) {
      return mostrarToast("Debe haber al menos una pregunta.", "error");
    }
    preguntas.splice(preguntaActual, 1);
    preguntaActual = Math.max(0, preguntaActual - 1);
    renderPreguntas();
    mostrarPregunta(preguntaActual);
  };

  // =============================
  //      MOSTRAR PREGUNTA
  // =============================
  function mostrarPregunta(index) {
    preguntaActual = index;
    const p = preguntas[index];

    inputPregunta.value = p.texto;

    if (p.imagen) {
      previewImg.src = p.imagen;
      previewContainer.style.display = "block";
      uploadArea.style.display = "none";
    } else {
      previewContainer.style.display = "none";
      uploadArea.style.display = "inline-flex";
    }

    tipoSel.value = p.tipo;

    mostrarComboCorrecta(false);
    renderCampoAbiertaPanel(p);
    renderRespuestas();
    renderPreguntas();
  }

  // =============================
  //   RENDER LATERAL IZQUIERDO
  // =============================
  function renderPreguntas() {
    lista.innerHTML = "";
    preguntas.forEach((p, i) => {
      const li = document.createElement("li");
      li.classList.add("preview-pregunta");
      if (i === preguntaActual) li.classList.add("active");

      const thumb = p.imagen
        ? `<img src="${p.imagen}" alt="img">`
        : `<span style="font-size:1.8rem; color:#e94e77;">🖼️</span>`;

      const opcionesHTML = p.opciones.map(o =>
        `<small class="${o.es_correcta ? "correcta" : ""}">${o.texto || (p.tipo === "Abierta" ? "[abierta]" : "(vacío)")}</small>`
      ).join("");

      li.innerHTML = `
        <div class="thumb">${thumb}</div>
        <span>${p.texto}</span>
        <div class="mini-opciones">${opcionesHTML}</div>
      `;

      li.onclick = () => mostrarPregunta(i);
      lista.appendChild(li);
    });
  }

  // ======================
  // RENDER OPCIONES CENTRO
  // ======================
  function renderRespuestas() {
    const p = preguntas[preguntaActual];
    respuestasContainer.innerHTML = "";

    btnMasRespuestas.style.display =
      (p.tipo === "Abierta" || p.tipo === "Verdadero/Falso") ? "none" : "inline-block";

    if (p.tipo === "Abierta") {
      respuestasContainer.innerHTML =
        `<div class="respuesta-abierta">
           <textarea readonly placeholder="El alumno escribirá aquí..."></textarea>
         </div>`;
      return;
    }

    if (p.tipo === "Verdadero/Falso") {
      ["Verdadero", "Falso"].forEach((texto, idx) => {
        const activo = !!p.opciones[idx]?.es_correcta;
        const div = document.createElement("div");
        div.className = `respuesta-tarjeta clicable ${activo ? "correcta" : ""}`;
        div.innerHTML = `<span class="opcion-label">${texto}</span>`;
        div.onclick = () => {
          p.opciones = [
            { texto: "Verdadero", es_correcta: texto === "Verdadero" },
            { texto: "Falso", es_correcta: texto === "Falso" }
          ];
          renderRespuestas();
          renderPreguntas();
        };
        respuestasContainer.appendChild(div);
      });
      return;
    }

    // Selección Simple / Múltiple
    p.opciones.forEach((op, i) => {
      const div = document.createElement("div");
      div.className = `respuesta-tarjeta ${op.es_correcta ? "correcta" : ""}`;

      const selector =
        p.tipo === "Selección Múltiple"
          ? `<input type="checkbox" class="seleccion-multiple" ${op.es_correcta ? "checked" : ""} />`
          : `<input type="radio" name="selecSimple" class="seleccion-simple" ${op.es_correcta ? "checked" : ""} />`;

      div.innerHTML = `
        ${selector}
        <input type="text" value="${op.texto}" class="input-opcion">
        <button class="btn-delete" title="Eliminar opción">🗑️</button>
      `;

      const chk = div.querySelector("input[type=checkbox], input[type=radio]");
      chk.onclick = () => {
        if (p.tipo === "Selección Simple") {
          p.opciones.forEach(o => (o.es_correcta = false));
          op.es_correcta = true;
        } else {
          op.es_correcta = chk.checked;
        }
        renderRespuestas();
        renderPreguntas();
      };

      div.querySelector(".btn-delete").onclick = () => {
        if (p.opciones.length <= 2)
          return mostrarToast("Debe haber mínimo 2 opciones", "error");
        p.opciones.splice(i, 1);
        renderRespuestas();
        renderPreguntas();
      };

      div.querySelector(".input-opcion").oninput = e => {
        op.texto = e.target.value;
        renderPreguntas();
      };

      respuestasContainer.appendChild(div);
    });
  }

  // Añadir opción
  btnMasRespuestas.onclick = e => {
    e.preventDefault();
    const p = preguntas[preguntaActual];
    p.opciones.push({ texto: `Opción ${p.opciones.length + 1}`, es_correcta: false });
    renderRespuestas();
    renderPreguntas();
  };

  // Cambiar tipo
  tipoSel.onchange = e => {
    const p = preguntas[preguntaActual];
    p.tipo = e.target.value;
    p.opciones = nuevaEstructuraOpciones(p.tipo);
    mostrarComboCorrecta(false);
    renderCampoAbiertaPanel(p);
    mostrarPregunta(preguntaActual);
  };

  // =============================
  //   IMÁGENES
  // =============================
  imagenInput.addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("imagen", file);

    try {
      const res = await fetch("/upload_imagen", { method: "POST", body: formData });
      const data = await res.json();

      if (data.url) {
        preguntas[preguntaActual].imagen = data.url;
        previewImg.src = data.url;
        previewContainer.style.display = "block";
        uploadArea.style.display = "none";
        renderPreguntas();
      }
    } catch {
      mostrarToast("No se pudo subir la imagen", "error");
    }
  });

  document.getElementById("btnEliminarImagen").onclick = () => {
    preguntas[preguntaActual].imagen = "";
    previewImg.src = "";
    previewContainer.style.display = "none";
    uploadArea.style.display = "inline-flex";
    renderPreguntas();
  };

  // =============================
  //   MODAL / GUARDAR
  // =============================
  btnPublicar.onclick = () => actualizarModal(true);
  btnCerrar.onclick = () => actualizarModal(false);

  function actualizarModal(v) {
    modal.classList.toggle("active", v);
    document.body.style.overflow = v ? "hidden" : "auto";
  }

  btnConfirmar.onclick = async () => {
    const titulo = document.getElementById("tituloCuestionario").value.trim();
    const descripcion = document.getElementById("descripcionCuestionario").value.trim();
    if (!titulo) return mostrarToast("Debe ingresar un título", "error");

    const payload = { titulo, descripcion, estado: "borrador", preguntas };

    try {
      let res;
      if (idCuestionario) {
        res = await fetch(`/cuestionario/${idCuestionario}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch("/crear-cuestionario", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }

      const data = await res.json();
      if (data.success) {
        mostrarToast(idCuestionario ? "✅ Cambios guardados" : "✅ Cuestionario guardado", "success");
        setTimeout(() => (window.location.href = "/biblioteca"), 1000);
      } else {
        mostrarToast("❌ " + (data.error || "Error al guardar"), "error");
      }
    } catch {
      mostrarToast("No se pudo conectar con el servidor", "error");
    }
  };

  // =============================
  // cargar cuestionario ya existente
  // =============================
  async function cargarCuestionarioExistente(id) {
    try {
      const res = await fetch(`/cuestionario/datos/${id}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "No encontrado");

      const q = data.cuestionario;
      document.getElementById('tituloCuestionario').value = q.titulo || '';
      document.getElementById('descripcionCuestionario').value = q.descripcion || '';

      preguntas = (q.preguntas || []).map(p => ({
        texto: p.texto,
        tipo: p.tipo,
        imagen: p.imagen || "",
        opciones: (p.opciones || []).map(o => ({ texto: o.texto, es_correcta: !!o.es_correcta }))
      }));

      if (preguntas.length === 0) agregarPregunta();

      renderPreguntas();
      mostrarPregunta(0);

      if (btnConfirmar) btnConfirmar.textContent = "Guardar cambios";

    } catch (e) {
      console.error(e);
      agregarPregunta();
    }
  }

  // =============================
  // TOAST
  // =============================
  function mostrarToast(msg, tipo = "info") {
    const t = document.createElement("div");
    t.className = `toast ${tipo}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add("show"), 10);
    setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => t.remove(), 300);
    }, 2500);
  }

  // =============================
  // vincular input título pregunta
  // =============================
  inputPregunta.addEventListener("input", e => {
    preguntas[preguntaActual].texto = e.target.value;
    renderPreguntas();
  });
});
