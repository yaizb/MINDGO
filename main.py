import uuid
import re
from flask import Flask, render_template, request, redirect, flash, session, url_for, jsonify, send_file
from flask_mail import Mail, Message
import pymysql
from bd import obtener_conexion
import controlador_usuarios
import controlador_cuestionarios
import controlador_roles
import controlador_lugares_trabajo
import controlador_tipo_preguntas
from controlador_usuarios import actualizar_avatar
import os
from werkzeug.utils import secure_filename
import pandas as pd
import io
import tempfile
from controlador_cuestionarios import (
    importar_cuestionario_desde_upload,
)

# ============================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================
app = Flask(__name__)
app.secret_key = 'clave_secreta'
salas_espera = {}

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'grupo3dawb@gmail.com'
app.config['MAIL_PASSWORD'] = 'ldysusqafgjqfgct'
app.config['MAIL_DEFAULT_SENDER'] = 'grupo3dawb@gmail.com'

mail = Mail(app)

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def validar_contrasena_fuerte(contrasena):
    """Valida que la contraseña cumpla con los requisitos de seguridad"""
    if len(contrasena) < 8:
        return False
    if not re.search(r"[A-Z]", contrasena):
        return False
    if not re.search(r"[a-z]", contrasena):
        return False
    if not re.search(r"[0-9]", contrasena):
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", contrasena):
        return False
    return True

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión válida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# RUTAS PRINCIPALES
# ============================================
@app.route("/")
def index():
    if 'usuario' in session:
        return redirect('/inicio_login')
    return render_template("index.html")


@app.route('/inicio_login')
def inicio_login():
    if 'usuario' in session:
        return render_template('inicio_login.html')
    else:
        return redirect('/login')

@app.route('/errorSistema')
def error_sistema():
    return render_template('errorSistema.html')

# ============================================
# RUTAS DE AUTENTICACIÓN
# ============================================
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/ingresar_usuario', methods=["POST"])
def ingresar_usuario():
    try:
        email = request.form["email"]
        contrasena = request.form["contrasena"]
        usuario = controlador_usuarios.obtener_usuario_por_email_y_contrasena(email, contrasena)

        if usuario:
            # usuario puede ser dict o tupla, manejar ambos casos
            if isinstance(usuario, dict):
                session['usuario'] = usuario['nombres']
                session['id_usuario'] = usuario.get('id')
                session['email'] = usuario.get('email')
                session['avatar'] = usuario.get('avatar', 'oveja.png')
            else:
                # usuario = (idUsuario, nombreUsuario, email, contraseña, idRol, idLugar)
                session['usuario'] = usuario[1]
                session['id_usuario'] = usuario[0]
                session['email'] = usuario[2]
                session['avatar'] = usuario[11] if len(usuario) > 11 and usuario[11] else 'oveja.png'

            flash('¡Bienvenido!', 'success')
            return redirect('/inicio_login')
        else:
            flash('Correo o contraseña incorrectos', 'error')
            return redirect('/login')
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        flash('Error al iniciar sesión. Por favor intenta de nuevo.', 'error')
        return redirect('/login')


@app.route('/registro', methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombres = request.form.get("nombres", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        email = request.form.get("email", "").strip()
        contrasena = request.form.get("contrasena", "")

        if not validar_contrasena_fuerte(contrasena):
            return render_template(
                "registro.html",
                error="La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.",
                nombres=nombres,
                apellidos=apellidos,
                email=email
            )

        token = controlador_usuarios.insertar_usuario_con_token(nombres, apellidos, email, contrasena)
        if token is None:
            return render_template(
                "registro.html",
                error="El correo ya está registrado.",
                nombres=nombres,
                apellidos=apellidos,
                email=email
            )

        enlace = url_for('verificar_email', token=token, _external=True)

        try:
            msg = Message(
                subject="Confirma tu cuenta - MindGo",
                recipients=[email],
                html=f"""
                <h3>¡Hola {nombres}!</h3>
                <p>Gracias por registrarte. Por favor, haz clic en el siguiente enlace para activar tu cuenta:</p>
                <a href="{enlace}" style="padding:10px 20px; background-color:#007BFF; color:white; text-decoration:none; border-radius:5px;">
                    Activar mi cuenta
                </a>
                <p>Si no te registraste, ignora este mensaje.</p>
                """
            )
            mail.send(msg)
            return render_template("verificacion.html")

        except Exception as e:
            print("Error al enviar correo:", str(e))
            return render_template(
                "registro.html",
                error="No se pudo enviar el correo de verificación. Inténtalo más tarde.",
                nombres=nombres,
                apellidos=apellidos,
                email=email
            )

    return render_template("registro.html")

@app.route("/verificar/<token>")
def verificar_email(token):
    if controlador_usuarios.verificar_usuario(token):
        return render_template("activar.html", exito="Tu cuenta ha sido activada. Ya puedes iniciar sesión.")
    else:
        return render_template("verificacion.html", error="El enlace de verificación es inválido o ya fue usado.")

@app.route('/verificacion')
def verificacion():
    return render_template('verificacion.html')

@app.route('/reenviar_verificacion', methods=["GET", "POST"])
def reenviar_verificacion():
    if request.method == "POST":
        email = request.form["email"].strip()
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombres, verificado FROM usuario WHERE email = %s", (email,))
            usuario = cursor.fetchone()

        if not usuario:
            return render_template("reenviar_verificacion.html", error="No existe una cuenta asociada a ese correo.")

        verificado = usuario[2]
        if verificado:
            return render_template("reenviar_verificacion.html", error="Tu cuenta ya está verificada. Puedes iniciar sesión.")

        # Generar nuevo token
        nuevo_token = str(uuid.uuid4())
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE usuario SET token_verificacion = %s WHERE email = %s",
                (nuevo_token, email)
            )
        conexion.commit()
        conexion.close()

        # Enviar nuevo correo
        enlace = url_for('verificar_email', token=nuevo_token, _external=True)
        try:
            msg = Message(
                subject="Reenvío: Confirma tu cuenta - MindGo",
                recipients=[email],
                html=f"""
                <h3>¡Hola {usuario[1]}!</h3>
                <p>Hemos reenviado tu enlace de verificación. Haz clic abajo para activar tu cuenta:</p>
                <a href="{enlace}" style="padding:10px 20px; background-color:#007BFF; color:white; text-decoration:none; border-radius:5px;">
                    Activar mi cuenta
                </a>
                """
            )
            mail.send(msg)
            return render_template("verificacion.html", mensaje="Se ha reenviado el correo de verificación.")
        except Exception as e:
            print("Error al reenviar correo:", e)
            return render_template("reenviar_verificacion.html", error="No se pudo reenviar el correo. Inténtalo más tarde.")

    return render_template("reenviar_verificacion.html")

@app.route('/recuperar_contrasenas', methods=["GET", "POST"])
def recuperar_contrasena():
    if request.method == "POST":
        email = request.form["email"].strip()
        token = controlador_usuarios.generar_token_recuperacion(email)
        if token:
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            try:
                msg = Message(
                    subject="Restablece tu contraseña - MindGo",
                    recipients=[email],
                    html=f"""
                    <h3>¿Olvidaste tu contraseña?</h3>
                    <p>Haz clic en el enlace para crear una nueva:</p>
                    <a href="{enlace}" style="padding:10px 20px; background-color:#007BFF; color:white; text-decoration:none; border-radius:5px;">
                        Restablecer contraseña
                    </a>
                    <p>El enlace expira en 1 hora.</p>
                    """
                )
                mail.send(msg)
                return render_template("mensaje_info.html", mensaje="Se ha enviado un enlace para restablecer tu contraseña.")
            except Exception as e:
                print("Error al enviar correo de recuperación:", e)
                return render_template("recuperar_contrasena.html", error="No se pudo enviar el correo.")
        else:
            return render_template("recuperar_contrasena.html", error="No hay ninguna cuenta verificada con ese correo.")
    return render_template("recuperar_contrasena.html")

@app.route('/restablecer/<token>', methods=["GET", "POST"])
def restablecer_contrasena(token):
    email = controlador_usuarios.validar_token_recuperacion(token)
    if not email:
        flash("El enlace es inválido o ha expirado.", "error")
        return redirect(url_for('login'))

    if request.method == "POST":
        nueva_contrasena = request.form["contrasena"].strip()
        if not validar_contrasena_fuerte(nueva_contrasena):
            return render_template("restablecer_contrasena.html", token=token, error="La contraseña no cumple con los requisitos.")
        controlador_usuarios.actualizar_contrasena(email, nueva_contrasena)
        flash("Contraseña actualizada con éxito.", "success")
        return redirect(url_for('login'))

    return render_template("restablecer_contrasena.html", token=token)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('id_usuario', None)
    session.pop('email', None)
    return redirect('/')

# ============================================
# RUTAS DE PERFIL
# ============================================

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'usuario' not in session:
        return redirect('/login')

    id_usuario = session.get('id_usuario')
    email = session.get('email')

    # 🔸 Si se envió el formulario de edición de datos
    if request.form.get('usuario') and request.form.get('email'):
        nuevo_usuario = request.form.get('usuario')
        nuevo_correo = request.form.get('email')
        try:
            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE usuario
                    SET nombres = %s, email = %s
                    WHERE id = %s
                """, (nuevo_usuario, nuevo_correo, id_usuario))
            conexion.commit()
            conexion.close()

            session['usuario'] = nuevo_usuario
            session['email'] = nuevo_correo
            flash('Datos actualizados correctamente ✅', 'success')
        except Exception as e:
            print(f"Error al actualizar datos: {e}")
            flash('Error al actualizar los datos.', 'error')

        return redirect('/perfil')

    # 🔸 Si se envió el formulario de cambio de contraseña
    if request.form.get('actual') and request.form.get('nueva'):
        actual = request.form.get('actual')
        nueva = request.form.get('nueva')
        confirmar = request.form.get('confirmar')

        try:
            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("SELECT contrasena FROM usuario WHERE email = %s", (email,))
                resultado = cursor.fetchone()

                if not resultado:
                    flash('Usuario no encontrado.', 'error')
                    return redirect('/perfil')

                contrasena_actual = resultado[0]

                if contrasena_actual != actual:
                    flash('La contraseña actual no es correcta.', 'error')
                    return redirect('/perfil')

                if nueva != confirmar:
                    flash('Las contraseñas no coinciden.', 'error')
                    return redirect('/perfil')

                cursor.execute("""
                    UPDATE usuario
                    SET contrasena = %s
                    WHERE email = %s
                """, (nueva, email))
            conexion.commit()
            conexion.close()

            flash('Contraseña actualizada correctamente ✅', 'success')
        except Exception as e:
            print(f"Error al cambiar contraseña: {e}")
            flash('Ocurrió un error al actualizar la contraseña.', 'error')

        return redirect('/perfil')

    # 🔸 Si es solo GET → mostrar la página normalmente
    return render_template(
        'perfil.html',
        usuario=session.get('usuario'),
        correo=session.get('email'),
        rol=session.get('rol', 'Estudiante'),
        avatar=session.get('avatar', 'oveja.png'),
        lugar_trabajo=session.get('lugar', 'Oficina Central'),
        verificado=session.get('verificado', True)
    )



@app.route('/cambiar_avatar', methods=['GET', 'POST'])
def cambiar_avatar():
    if 'id_usuario' not in session:
        return redirect('/login')

    avatares = [
        'oveja.png', 'buho.png', 'dragon.png',
        'koala.png', 'camello.png', 'vaca.png',
        'reno.png', 'delfin.png', 'pulpo.png'
    ]

    if request.method == 'POST':
        avatar_seleccionado = request.form.get('avatar')
        if avatar_seleccionado and avatar_seleccionado in avatares:
            usuario_id = session['id_usuario']
            if actualizar_avatar(usuario_id, avatar_seleccionado):
                session['avatar'] = avatar_seleccionado
                flash('¡Avatar guardado con éxito!', 'success')
            else:
                flash('Error al guardar el avatar.', 'error')
            return redirect('/perfil')  # o '/inicio_login' si ese es tu perfil

    avatar_actual = session.get('avatar', 'oveja.png')
    return render_template('cambiar_avatar.html',
                           avatares=avatares,
                           avatar_actual=avatar_actual)

# ============================================
# RUTAS DE BIBLIOTECA
# ============================================
@app.route('/biblioteca')
def biblioteca():
    if 'usuario' not in session:
        return redirect('/login')
    return render_template('biblioteca.html')

@app.route('/biblioteca/mis-cuestionarios')
def mis_cuestionarios():
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        id_usuario = session.get('id_usuario')
        cuestionarios = controlador_cuestionarios.obtener_cuestionarios_usuario(id_usuario)

        return jsonify({
            'success': True,
            'cuestionarios': cuestionarios
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/biblioteca/favorito/<int:id_cuestionario>', methods=['POST'])
def toggle_favorito(id_cuestionario):
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        id_usuario = session.get('id_usuario')
        es_favorito = controlador_cuestionarios.toggle_favorito(id_cuestionario, id_usuario)

        return jsonify({
            'success': True,
            'es_favorito': es_favorito
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/biblioteca/papelera/<int:id_cuestionario>', methods=['POST'])
def mover_papelera(id_cuestionario):
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        id_usuario = session.get('id_usuario')
        controlador_cuestionarios.mover_a_papelera(id_cuestionario, id_usuario)

        return jsonify({
            'success': True,
            'mensaje': 'Cuestionario movido a la papelera'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/biblioteca/restaurar/<int:id_cuestionario>', methods=['POST'])
def restaurar_cuestionario(id_cuestionario):
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        id_usuario = session.get('id_usuario')
        controlador_cuestionarios.restaurar_cuestionario(id_cuestionario, id_usuario)

        return jsonify({
            'success': True,
            'mensaje': 'Cuestionario restaurado'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/biblioteca/eliminar/<int:id_cuestionario>', methods=['DELETE'])
def eliminar_cuestionario_biblioteca(id_cuestionario):
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        controlador_cuestionarios.eliminar_cuestionario(id_cuestionario)
        return jsonify({
            'success': True,
            'mensaje': 'Cuestionario eliminado'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/biblioteca/limpiar-papelera', methods=['DELETE'])
def limpiar_papelera():
    if 'usuario' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        id_usuario = session.get('id_usuario')
        eliminados = controlador_cuestionarios.limpiar_papelera(id_usuario)
        return jsonify({
            'success': True,
            'eliminados': eliminados,
            'mensaje': f'{eliminados} cuestionario(s) eliminado(s)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/cuestionarios/plantilla-simple")
def plantilla_simple():
    """
    Devuelve un Excel de ejemplo con las columnas esperadas:
    Pregunta | Respuesta | Alternativa A | Alternativa B | Alternativa C | Alternativa D
    """
    data = [{
        "Pregunta": "Capital de Francia",
        "Respuesta": "París",
        "Alternativa A": "París",
        "Alternativa B": "Londres",
        "Alternativa C": "Roma",
        "Alternativa D": "Berlín",
    }]
    df = pd.DataFrame(data)

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cuestionario")

    bio.seek(0)
    return send_file(
        bio,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="plantilla_cuestionario.xlsx"
    )


# ------------------------------------------------------------------------------------
# 📤 RUTA: Importar cuestionario desde archivo Excel/CSV
# ------------------------------------------------------------------------------------
@app.route("/cuestionarios/importar-simple", methods=["POST"])
def importar_simple():
    """
    Procesa un archivo Excel/CSV con preguntas y crea o actualiza un cuestionario.

    Form-data esperado:
    - archivo: (file) Excel o CSV
    - idUsuario: (int) ID del usuario que importa
    - idCuestionario: (int, opcional) Si se quiere agregar preguntas a un cuestionario existente
    - tituloSiCrea: (str, opcional) Título si se crea uno nuevo
    """
    try:
        # Obtener los datos del formulario
        file = request.files.get("archivo")
        id_usuario = request.form.get("idUsuario")
        id_cuestionario = request.form.get("idCuestionario") or None
        titulo_si_crea = request.form.get("tituloSiCrea") or None

        if not id_usuario:
            flash("Falta el ID del usuario.", "danger")
            return redirect(url_for("biblioteca"))

        id_usuario = int(id_usuario)
        id_cuestionario = int(id_cuestionario) if id_cuestionario else None

        # Llamar al controlador
        resultado = importar_cuestionario_desde_upload(
            file_storage=file,
            id_usuario=id_usuario,
            id_cuestionario=id_cuestionario,
            titulo_si_crea=titulo_si_crea
        )

        # Si la petición viene por fetch (AJAX)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            status = 200 if resultado.get("estado") == "ok" else 400
            return jsonify(resultado), status

        # Si se envía desde formulario normal
        if resultado.get("estado") == "ok":
            msg = (
                f"Importación exitosa. "
                f"Preguntas: {resultado.get('preguntas', 0)}, "
                f"Respuestas: {resultado.get('respuestas', 0)}."
            )
            flash(msg, "success")
        else:
            flash(resultado.get("mensaje", "Error durante la importación."), "danger")

    except Exception as e:
        flash(f"Ocurrió un error al procesar la importación: {e}", "danger")

    return redirect(url_for("biblioteca"))

# ============================================
# RUTAS DE CUESTIONARIOS
# ============================================
@app.route('/cuestionario')
def cuestionario():
    quiz_id = request.args.get('id', default='', type=str)
    return render_template('crear_cuestionario.html', id_cuestionario=quiz_id)

@app.route('/crear-cuestionario', methods=['POST'])
def crear_cuestionario():
    from controlador_cuestionarios import crear_cuestionario as crear, guardar_pregunta

    if 'id_usuario' not in session:
        return jsonify(success=False, error="Usuario no autenticado"), 401

    data = request.get_json()
    titulo = data.get('titulo')
    descripcion = data.get('descripcion', '')
    estado = data.get('estado', 'borrador')
    preguntas = data.get('preguntas', [])
    id_usuario = session.get('id_usuario')

    try:
        print(f"📩 Recibiendo cuestionario: {titulo} ({len(preguntas)} preguntas)")

        # Crear cuestionario
        id_cuestionario = crear(titulo, id_usuario, descripcion)
        print(f"✅ Cuestionario creado con ID {id_cuestionario}")

        # Guardar cada pregunta
        for i, p in enumerate(preguntas, start=1):
            texto_pregunta = p.get('texto', '').strip()
            if not texto_pregunta:
                continue

            opciones = []
            for o in p.get('opciones', []):
                if isinstance(o, dict):
                    texto = o.get('texto', '').strip()
                    correcta = o.get('es_correcta', False)
                else:
                    texto = str(o).strip()
                    correcta = False
                if texto:
                    opciones.append({'texto': texto, 'es_correcta': correcta, 'color': 'Azul'})

            guardar_pregunta(
                id_cuestionario=id_cuestionario,
                numero_pregunta=i,
                texto_pregunta=texto_pregunta,
                tipo_pregunta='quiz',
                tiempo_limite=30,
                puntos=5,
                opciones=opciones,
                url_multimedia=p.get('imagen')
            )

        print("✅ Preguntas guardadas correctamente")
        return jsonify(success=True, id=id_cuestionario)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("❌ Error al guardar cuestionario:", e)
        return jsonify(success=False, error=str(e)), 500


# --- NUEVO: datos para precargar el editor ---
@app.route('/cuestionario/datos/<int:id_cuestionario>')
def datos_cuestionario(id_cuestionario):
    from controlador_cuestionarios import obtener_cuestionario
    data = obtener_cuestionario(id_cuestionario)
    if not data:
        return jsonify(success=False, error="No existe"), 404

    # Adaptamos lo que devuelve tu controlador al formato del front
    cu = data['cuestionario']
    salida = {
        "id": id_cuestionario,
        "titulo": cu[1] if len(cu) > 1 else "Sin título",
        "descripcion": cu[4] if len(cu) > 4 else "",
        "preguntas": []
    }

    for pack in data['preguntas']:
        preg = pack['pregunta']     # (idPregunta, descripcion, ordenInterno, limiteTiempo, puntos, urlMultimedia, idTipoPregunta, idCuestionario)
        ops  = pack['opciones']     # [(idRespuesta, descripcion, esCorrecta, idPregunta, idFormato), ...]

        opciones = [{"texto": r[1], "es_correcta": bool(r[2])} for r in ops]

        # Inferimos tipo según opciones
        textos = [o["texto"].strip().lower() for o in opciones]
        correctas = sum(1 for o in opciones if o["es_correcta"])
        if len(opciones) == 2 and set(textos) == {"verdadero", "falso"}:
            tipo = "Verdadero/Falso"
        elif correctas > 1:
            tipo = "Selección Múltiple"
        else:
            tipo = "Selección Simple"

        salida["preguntas"].append({
            "texto": preg[1],
            "tipo": tipo,
            "imagen": preg[5] or "",
            "opciones": opciones
        })

    return jsonify(success=True, cuestionario=salida)


# --- NUEVO: actualizar cuestionario completo ---
@app.route('/cuestionario/<int:id_cuestionario>', methods=['PUT'])
def actualizar_cuestionario_api(id_cuestionario):
    if 'id_usuario' not in session:
        return jsonify(success=False, error="Usuario no autenticado"), 401

    from controlador_cuestionarios import guardar_pregunta
    data = request.get_json() or {}
    titulo = data.get('titulo', '').strip()
    descripcion = data.get('descripcion', '').strip()
    preguntas = data.get('preguntas', [])

    if not titulo:
        return jsonify(success=False, error="Título requerido"), 400

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cur:
            # 1) actualizar cabecera
            cur.execute("""UPDATE CUESTIONARIO
                           SET titulo=%s, descripcion=%s, estado='borrador'
                           WHERE idCuestionario=%s""",
                        (titulo, descripcion, id_cuestionario))

            # 2) borrar preguntas y respuestas actuales
            cur.execute("SELECT idPregunta FROM PREGUNTAS WHERE idCuestionario=%s", (id_cuestionario,))
            ids = [r[0] for r in cur.fetchall()]
            for pid in ids:
                cur.execute("DELETE FROM RESPUESTAS WHERE idPregunta=%s", (pid,))
            cur.execute("DELETE FROM PREGUNTAS WHERE idCuestionario=%s", (id_cuestionario,))
            conexion.commit()

        # 3) reinsertar con tu helper
        for i, p in enumerate(preguntas, start=1):
            if not p.get('texto', '').strip():
                continue
            opciones = []
            for o in p.get('opciones', []):
                if not o.get('texto', '').strip():
                    continue
                opciones.append({'texto': o['texto'].strip(),
                                 'es_correcta': bool(o.get('es_correcta', False)),
                                 'color': 'Azul'})
            guardar_pregunta(
                id_cuestionario=id_cuestionario,
                numero_pregunta=i,
                texto_pregunta=p['texto'].strip(),
                tipo_pregunta='quiz',         # usa el mismo mapeo que ya tienes
                tiempo_limite=30,
                puntos=5,
                opciones=opciones,
                url_multimedia=p.get('imagen') or None
            )

        return jsonify(success=True, id=id_cuestionario)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conexion.close()


@app.route('/upload_imagen', methods=['POST'])
def upload_imagen():
    if 'imagen' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['imagen']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400


    filename = secure_filename(file.filename)


    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)

    url = f"/static/uploads/{filename}"
    print(f"✅ Imagen guardada en: {save_path}")
    return jsonify({'url': url})


@app.route('/tipos-pregunta')
def tipos_pregunta():
    from bd import obtener_conexion
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT nombre FROM TIPO_PREGUNTA ORDER BY nombre ASC")
            tipos = [row[0] for row in cursor.fetchall()]
        return jsonify(tipos)
    finally:
        conexion.close()

# ============================================
# RUTAS DE SALA DE ESPERA Y RANKING
# ============================================
@app.route('/salaEspera')
def salaEspera():
    if 'usuario' not in session:
        return redirect('/login')

    # Verificar si viene con PIN (participante) o con ID de cuestionario (creador)
    pin_ingresado = request.args.get('pin')
    id_cuestionario = request.args.get('id')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        if id_cuestionario:
            # MODO CREADOR: Verificar que el cuestionario pertenece al usuario
            cursor.execute("""
                SELECT idCuestionario, titulo, descripcion, idUsuario
                FROM CUESTIONARIO
                WHERE idCuestionario = %s
            """, (id_cuestionario,))
            cuestionario = cursor.fetchone()

            if not cuestionario:
                return redirect('/biblioteca')

            # Verificar que el usuario es el creador
            if cuestionario[3] != session.get('id_usuario'):
                flash('No tienes permiso para gestionar este cuestionario', 'error')
                return redirect('/biblioteca')

            # Buscar si ya existe una sesión activa para este cuestionario y usuario
            cursor.execute("""
                SELECT pin, idSesion FROM SESION_JUEGO
                WHERE idCuestionario = %s
                AND idUsuarioCreador = %s
                AND estado IN ('esperando', 'en_progreso')
                ORDER BY idSesion DESC
                LIMIT 1
            """, (id_cuestionario, session.get('id_usuario')))

            sesion_existente = cursor.fetchone()

            if sesion_existente:
                # Ya existe una sesión, usar el PIN existente
                pin_sala = sesion_existente[0]
                id_sesion = sesion_existente[1]

                # Verificar el estado de la sesión
                cursor.execute("""
                    SELECT estado FROM SESION_JUEGO WHERE idSesion = %s
                """, (id_sesion,))
                estado = cursor.fetchone()[0]

                # Si el juego ya está en progreso, redirigir al juego (no a sala de espera)
                if estado == 'en_progreso':
                    flash('El juego ya está en curso', 'info')
                    return redirect(f'/jugar?id={id_cuestionario}&pin={pin_sala}')
            else:
                # Primera vez: Generar PIN único
                import random
                while True:
                    pin_sala = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    # Verificar que el PIN no esté en uso
                    cursor.execute("""
                        SELECT COUNT(*) FROM SESION_JUEGO
                        WHERE pin = %s AND estado IN ('esperando', 'en_progreso')
                    """, (pin_sala,))
                    if cursor.fetchone()[0] == 0:
                        break

                # Crear la sesión en la base de datos
                cursor.execute("""
                    INSERT INTO SESION_JUEGO
                    (pin, modo, estado, temporizadorPreguntas, ordenAlternativasAzar,
                     idCuestionario, idUsuarioCreador, fechaHoraInicio)
                    VALUES (%s, 'clasico', 'esperando', 30, 1, %s, %s, NOW())
                """, (pin_sala, id_cuestionario, session.get('id_usuario')))

                id_sesion = cursor.lastrowid
                conexion.commit()

            # Inicializar sala en memoria si no existe
            if pin_sala not in salas_espera:
                salas_espera[pin_sala] = {
                    "config": {
                        "modo": "individual",
                        "grupos": None,
                        "maxIntegrantes": None
                    },
                    "participantes": [],
                    "abierta": True,
                    "id_cuestionario": id_cuestionario,
                    "id_sesion": id_sesion,
                    "creador_id": session.get('id_usuario')
                }

            # Pasar datos al template
            return render_template('salaEspera.html',
                                 es_creador=True,
                                 pin=pin_sala,
                                 id_cuestionario=id_cuestionario,
                                 cuestionario_titulo=cuestionario[1],
                                 cuestionario_descripcion=cuestionario[2])

        elif pin_ingresado:
            # MODO PARTICIPANTE: Unirse con PIN
            pin_limpio = pin_ingresado.replace(' ', '')

            # Verificar que el PIN existe en la base de datos
            cursor.execute("""
                SELECT s.idSesion, s.idCuestionario, s.estado, s.idUsuarioCreador,
                       c.titulo, c.descripcion
                FROM SESION_JUEGO s
                JOIN CUESTIONARIO c ON s.idCuestionario = c.idCuestionario
                WHERE s.pin = %s AND s.estado IN ('esperando', 'en_progreso')
            """, (pin_limpio,))

            sesion = cursor.fetchone()

            if not sesion:
                flash('PIN inválido o sesión no disponible', 'error')
                return redirect('/')

            # Verificar si el usuario actual es el creador
            if sesion[3] == session.get('id_usuario'):
                # Es el creador accediendo con PIN, mostrar interfaz de control
                return render_template('salaEspera.html',
                                     es_creador=True,
                                     pin=pin_limpio,
                                     id_cuestionario=sesion[1],
                                     cuestionario_titulo=sesion[4],
                                     cuestionario_descripcion=sesion[5])
            else:
                # Es un participante normal - INCLUIR id_cuestionario
                return render_template('salaEspera.html',
                                     es_creador=False,
                                     pin=pin_limpio,
                                     id_cuestionario=sesion[1],  # ← AGREGADO
                                     cuestionario_titulo=sesion[4])
        else:
            # No hay ni PIN ni ID, redirigir
            return redirect('/biblioteca')

    except Exception as e:
        print(f"Error en salaEspera: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al cargar la sala de espera', 'error')
        return redirect('/biblioteca')
    finally:
        cursor.close()
        conexion.close()

@app.route('/registrar_sala', methods=['POST'])
def registrar_sala():
    data = request.get_json()
    pin = data.get('pin')
    modo = data.get('modo', 'individual')
    grupos = data.get('grupos')
    maxIntegrantes = data.get('maxIntegrantes')

    if not pin or len(pin) != 6 or not pin.isdigit():
        return jsonify({"error": "PIN inválido"}), 400

    # Guardar la configuración de la sala
    salas_espera[pin] = {
        "config": {
            "modo": modo,
            "grupos": grupos,
            "maxIntegrantes": maxIntegrantes
        },
        "participantes": [],
        "abierta": True
    }

    return jsonify({"success": True})

@app.route('/api/config_sala')
def config_sala():
    pin = (request.args.get('pin') or '').replace(' ', '')
    if not pin or len(pin) != 6 or not pin.isdigit():
        return jsonify({"error": "PIN inválido"}), 400

    sala = salas_espera.get(pin)
    if not sala:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                SELECT idSesion, idCuestionario, idUsuarioCreador, estado
                FROM SESION_JUEGO
                WHERE pin = %s
            """, (pin,))
            s = cursor.fetchone()
            if not s:
                return jsonify({"error": "Sala no encontrada"}), 404
            estado = s[3]
            if estado not in ('esperando', 'en_progreso'):
                return jsonify({"error": "La sala está cerrada"}), 403

            salas_espera[pin] = {
                "config": {"modo": "individual", "grupos": None, "maxIntegrantes": None},
                "participantes": [],
                "abierta": True,
                "estado": estado,
                "id_cuestionario": s[1],
                "id_sesion": s[0],
                "creador_id": s[2]
            }
            sala = salas_espera[pin]
        finally:
            cursor.close()
            conexion.close()

    config = sala.get("config", {})
    return jsonify({
        "modo": config.get("modo", "individual"),
        "grupos": config.get("grupos"),
        "maxIntegrantes": config.get("maxIntegrantes"),
        "estado": sala.get("estado", "esperando"),
        "abierta": sala.get("abierta", True)
    })



@app.route('/unirse_sala', methods=['POST'])
def unirse_sala():
        data = request.get_json()
        pin = (data.get('pin') or '').replace(' ', '')
        nombre = data.get('nombre')
        avatar = data.get('avatar') or 'oveja.png'
        grupo = data.get('grupo')

        if not pin or not nombre:
            return jsonify({"error": "Faltan datos"}), 400

        # Si la sala no está en memoria, intenta reconstruirla desde BD
        if pin not in salas_espera:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("""
                    SELECT idSesion, idCuestionario, idUsuarioCreador, estado
                    FROM SESION_JUEGO
                    WHERE pin = %s
                """, (pin,))
                s = cursor.fetchone()
                if not s:
                    return jsonify({"error": "Sala no encontrada"}), 404

                estado = s[3]
                # Solo permitimos unirse si está esperando o en progreso
                if estado not in ('esperando', 'en_progreso'):
                    return jsonify({"error": "La sala está cerrada"}), 403

                salas_espera[pin] = {
                    "config": {
                        "modo": "individual",
                        "grupos": None,
                        "maxIntegrantes": None
                    },
                    "participantes": [],
                    "abierta": True,         # <- abierta por defecto si está operativa
                    "estado": estado,        # <- sincroniza estado
                    "id_cuestionario": s[1],
                    "id_sesion": s[0],
                    "creador_id": s[2]
                }
            finally:
                cursor.close()
                conexion.close()

        sala = salas_espera[pin]

        # Si la sesión en memoria indica que no está operativa, bloquear
        if sala.get("estado") not in ('esperando', 'en_progreso'):
            return jsonify({"error": "La sala está cerrada"}), 403

        if not sala.get("abierta", True):
            return jsonify({"error": "La sala está bloqueada."}), 403

        # Registrar participante en BASE DE DATOS primero
        id_sesion = sala.get("id_sesion")
        id_usuario = session.get('id_usuario')

        participante_id_bd = None

        if not id_sesion:
            return jsonify({"error": "Sesión no encontrada en sala"}), 500

        if not id_usuario:
            return jsonify({"error": "Debes iniciar sesión primero"}), 401

        try:
            conexion_bd = obtener_conexion()
            cursor_bd = conexion_bd.cursor()

            # Verificar si ya existe el participante
            cursor_bd.execute("""
                SELECT idParticipante FROM PARTICIPANTE
                WHERE idSesion = %s AND idUsuario = %s
            """, (id_sesion, id_usuario))

            participante_existente = cursor_bd.fetchone()

            if participante_existente:
                # Actualizar datos (reconexión)
                cursor_bd.execute("""
                    UPDATE PARTICIPANTE
                    SET nickName = %s, avatar = %s, fechaHoraIngreso = NOW()
                    WHERE idParticipante = %s
                """, (nombre, avatar, participante_existente[0]))
                participante_id_bd = participante_existente[0]
                print(f"✅ Participante actualizado en BD: ID={participante_id_bd}, nombre={nombre}")
            else:
                # Crear nuevo participante
                cursor_bd.execute("""
                    INSERT INTO PARTICIPANTE
                    (idSesion, idUsuario, nickName, avatar, fechaHoraIngreso, puntajeFinal, preguntasAcertadas)
                    VALUES (%s, %s, %s, %s, NOW(), 0, 0)
                """, (id_sesion, id_usuario, nombre, avatar))
                participante_id_bd = cursor_bd.lastrowid
                print(f"✅ Nuevo participante creado en BD: ID={participante_id_bd}, nombre={nombre}")

            conexion_bd.commit()
            cursor_bd.close()
            conexion_bd.close()

        except Exception as e:
            print(f"❌ Error al registrar participante en BD: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Error al registrar en BD: {str(e)}"}), 500

        # Registrar participante en MEMORIA (usando el ID de BD como referencia)
        # Verificar si ya está en memoria
        participante_en_memoria = None
        for p in sala["participantes"]:
            if p.get('id_bd') == participante_id_bd:
                participante_en_memoria = p
                break

        if participante_en_memoria:
            # Actualizar datos en memoria
            participante_en_memoria['name'] = nombre
            participante_en_memoria['avatar'] = avatar
            participante_en_memoria['grupo'] = grupo
            print(f"✅ Participante actualizado en memoria: {nombre}")
        else:
            # Agregar nuevo a memoria
            sala["participantes"].append({
                "id": str(uuid.uuid4()),  # ID temporal para referencia en memoria
                "id_bd": participante_id_bd,  # ID real de la BD
                "name": nombre,
                "avatar": avatar,
                "grupo": grupo
            })
            print(f"✅ Participante agregado a memoria: {nombre}")

        return jsonify({
            "success": True,
            "id_participante": participante_id_bd,  # Usar el ID de BD como principal
            "mensaje": "Participante registrado correctamente"
        })

@app.route('/seleccionar_grupo', methods=['POST'])
def seleccionar_grupo():
    data = request.get_json()
    pin = data.get('pin')
    participante_id = data.get('participante_id')
    grupo = data.get('grupo')

    if not pin or not participante_id or grupo is None:
        return jsonify({"error": "Faltan datos"}), 400

    if pin in salas_espera:
        for p in salas_espera[pin]["participantes"]:
            if p.get('id') == participante_id:
                p['grupo'] = grupo
                return jsonify({"success": True})
    return jsonify({"error": "Participante no encontrado"}), 404

@app.route('/mover_grupo', methods=['POST'])
def mover_grupo():
    data = request.get_json()
    pin = data.get('pin')
    participante_id = data.get('participante_id')
    nuevo_grupo = data.get('nuevo_grupo')

    if not pin or not participante_id or nuevo_grupo is None:
        return jsonify({"error": "Faltan datos"}), 400

    if pin in salas_espera:
        for p in salas_espera[pin]["participantes"]:
            if p.get('id') == participante_id:
                p['grupo'] = nuevo_grupo
                return jsonify({"success": True})
    return jsonify({"error": "Participante no encontrado"}), 404

@app.route('/salir_sala', methods=['POST'])
def salir_sala():
    data = request.get_json()
    pin = data.get('pin')
    participante_id = data.get('participante_id')

    if not pin or not participante_id:
        return jsonify({"error": "Faltan datos"}), 400

    if pin in salas_espera:
        salas_espera[pin]["participantes"] = [
            p for p in salas_espera[pin]["participantes"]
            if p.get('id') != participante_id
        ]

    return jsonify({"status": "ok"})

@app.route('/obtener_participantes')
def obtener_participantes():
    pin = request.args.get('pin', '').replace(' ', '')
    sala = salas_espera.get(pin, {"participantes": [], "estado": "esperando"})

    # Obtener estado actual de la base de datos
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            SELECT estado FROM SESION_JUEGO WHERE pin = %s
        """, (pin,))

        resultado = cursor.fetchone()
        if resultado:
            estado_db = resultado[0]
            sala['estado'] = estado_db
            # Actualizar también en memoria
            if pin in salas_espera:
                salas_espera[pin]['estado'] = estado_db
    except Exception as e:
        print(f"Error al obtener estado: {e}")
    finally:
        cursor.close()
        conexion.close()

    return jsonify({
        "participantes": sala["participantes"],
        "estado": sala.get("estado", "esperando"),
        "success": True
    })

@app.route('/eliminar_participante', methods=['POST'])
def eliminar_participante():
    data = request.get_json()
    pin = data.get('pin', '').replace(' ', '')
    nombre = data.get('nombre')
    avatar = data.get('avatar')

    if not pin or not nombre:
        return jsonify({"error": "PIN y nombre son requeridos"}), 400

    if pin not in salas_espera:
        return jsonify({"error": "Sala no encontrada"}), 404

    sala = salas_espera[pin]
    participantes = sala["participantes"]
    for i, p in enumerate(participantes):
        if p['name'] == nombre and p.get('avatar') == avatar:
            del participantes[i]
            return jsonify({"success": True}), 200

    return jsonify({"error": "Participante no encontrado"}), 404

# ============================================
# RUTAS DE JUEGO
# ============================================
@app.route('/jugar')
def jugar():
    """Página principal del juego"""
    if 'usuario' not in session:
        return redirect('/login')

    pin = request.args.get('pin')
    id_cuestionario = request.args.get('id')
    modo = request.args.get('modo', 'individual')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Obtener información del cuestionario
        cursor.execute("""
            SELECT c.idCuestionario, c.titulo, c.descripcion,
                   COUNT(p.idPregunta) as num_preguntas
            FROM CUESTIONARIO c
            LEFT JOIN PREGUNTAS p ON c.idCuestionario = p.idCuestionario
            WHERE c.idCuestionario = %s
            GROUP BY c.idCuestionario
        """, (id_cuestionario,))

        cuestionario = cursor.fetchone()

        if not cuestionario:
            flash('Cuestionario no encontrado', 'error')
            return redirect('/biblioteca')

        # Buscar la sesión activa
        if pin:
            pin_limpio = pin.replace(' ', '')
            cursor.execute("""
                SELECT idSesion, pin, estado
                FROM SESION_JUEGO
                WHERE pin = %s
            """, (pin_limpio,))
        else:
            cursor.execute("""
                SELECT idSesion, pin, estado
                FROM SESION_JUEGO
                WHERE idCuestionario = %s
                AND idUsuarioCreador = %s
                AND estado IN ('esperando', 'en_progreso')
                ORDER BY idSesion DESC
                LIMIT 1
            """, (id_cuestionario, session.get('id_usuario')))

        sesion = cursor.fetchone()

        if sesion:
            id_sesion = sesion[0]
            pin_juego = sesion[1]
            estado_sesion = sesion[2]

            # Validar que la sesión esté activa
            if estado_sesion == 'finalizado':
                flash('Esta sesión de juego ya finalizó', 'error')
                return redirect('/biblioteca')

            # Validar que la sesión no esté cerrada
            if estado_sesion not in ['esperando', 'en_progreso']:
                flash('Esta sesión de juego no está disponible', 'error')
                return redirect('/biblioteca')

            # Actualizar estado de la sesión a "en_progreso" si estaba esperando
            if estado_sesion == 'esperando':
                cursor.execute("""
                    UPDATE SESION_JUEGO
                    SET estado = 'en_progreso'
                    WHERE idSesion = %s
                """, (id_sesion,))
                conexion.commit()
        else:
            flash('Sesión no encontrada', 'error')
            return redirect('/biblioteca')

        # Verificar rol del usuario
        es_creador = False
        cursor.execute("""
            SELECT idUsuarioCreador FROM SESION_JUEGO WHERE idSesion = %s
        """, (id_sesion,))
        creador = cursor.fetchone()
        if creador and creador[0] == session.get('id_usuario'):
            es_creador = True

        # Buscar si el usuario ya tiene un registro de participante (para reconexión)
        id_participante = None
        if not es_creador:
            cursor.execute("""
                SELECT idParticipante, nickName
                FROM PARTICIPANTE
                WHERE idSesion = %s AND idUsuario = %s
            """, (id_sesion, session.get('id_usuario')))

            participante = cursor.fetchone()
            if participante:
                id_participante = participante[0]
                print(f"✅ Participante encontrado en BD para /jugar: ID={id_participante}, Nombre={participante[1]}")
            else:
                print(f"⚠️ Participante NO encontrado en BD. idSesion={id_sesion}, idUsuario={session.get('id_usuario')}")
                print(f"   El participante se registrará automáticamente al cargar la página")

        return render_template('jugar.html',
                             id_cuestionario=id_cuestionario,
                             id_sesion=id_sesion,
                             pin=pin_juego,
                             titulo=cuestionario[1],
                             descripcion=cuestionario[2],
                             num_preguntas=cuestionario[3],
                             modo=modo,
                             es_creador=es_creador,
                             id_participante=id_participante)

    except Exception as e:
        print(f"Error en /jugar: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al iniciar el juego', 'error')
        return redirect('/biblioteca')
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/obtener-pregunta/<int:id_cuestionario>/<int:numero>')
def obtener_pregunta(id_cuestionario, numero):
    """Obtiene una pregunta específica del cuestionario"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Obtener la pregunta
        cursor.execute("""
            SELECT p.idPregunta, p.descripcion, p.limiteTiempo, p.puntos,
                   p.urlMultimedia, tp.nombre as tipo_pregunta
            FROM PREGUNTAS p
            JOIN TIPO_PREGUNTA tp ON p.idTipoPregunta = tp.idTipoPregunta
            WHERE p.idCuestionario = %s AND p.ordenInterno = %s
        """, (id_cuestionario, numero))

        pregunta = cursor.fetchone()

        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404

        # Obtener respuestas
        cursor.execute("""
            SELECT r.idRespuestas, r.descripcion, r.esCorrecta, f.color, f.icono
            FROM RESPUESTAS r
            LEFT JOIN FORMATO_RESPUESTA f ON r.idFormato = f.idFormato
            WHERE r.idPregunta = %s
            ORDER BY r.idRespuestas
        """, (pregunta[0],))

        respuestas = cursor.fetchall()

        opciones = []
        for resp in respuestas:
            opciones.append({
                'id': resp[0],
                'texto': resp[1],
                'es_correcta': bool(resp[2]),
                'color': resp[3] or '#1368CE',
                'icono': resp[4] or '🔷'
            })

        return jsonify({
            'success': True,
            'pregunta': {
                'id': pregunta[0],
                'texto': pregunta[1],
                'tiempo_limite': pregunta[2],
                'puntos': pregunta[3],
                'imagen': pregunta[4],
                'tipo': pregunta[5],
                'opciones': opciones
            }
        })

    except Exception as e:
        print(f"Error al obtener pregunta: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/guardar-respuesta', methods=['POST'])
def guardar_respuesta():
    """Guarda la respuesta de un participante"""
    data = request.get_json()

    id_participante = data.get('id_participante')
    id_pregunta = data.get('id_pregunta')
    id_respuesta = data.get('id_respuesta')
    tiempo_respuesta = data.get('tiempo_respuesta')

    print(f"\n📝 Guardando respuesta:")
    print(f"   - ID Participante: {id_participante}")
    print(f"   - ID Pregunta: {id_pregunta}")
    print(f"   - ID Respuesta: {id_respuesta}")
    print(f"   - Tiempo: {tiempo_respuesta}s")

    if not all([id_participante, id_pregunta]):
        print(f"❌ Error: Faltan datos obligatorios")
        return jsonify({'error': 'Faltan datos'}), 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Verificar que el participante existe
        cursor.execute("""
            SELECT idParticipante, nickName FROM PARTICIPANTE
            WHERE idParticipante = %s
        """, (id_participante,))

        participante = cursor.fetchone()
        if not participante:
            print(f"❌ Error: Participante {id_participante} no encontrado en BD")
            return jsonify({'error': 'Participante no encontrado'}), 404

        print(f"✅ Participante encontrado: {participante[1]}")

        # Verificar si la respuesta es correcta
        es_correcta = False
        puntos_obtenidos = 0
        id_respuesta_correcta = None

        if id_respuesta:
            cursor.execute("""
                SELECT r.esCorrecta, p.puntos
                FROM RESPUESTAS r
                JOIN PREGUNTAS p ON r.idPregunta = p.idPregunta
                WHERE r.idRespuestas = %s
            """, (id_respuesta,))

            resultado = cursor.fetchone()
            if resultado:
                es_correcta = bool(resultado[0])
                puntos_base = resultado[1]

                # Calcular puntos según tiempo (bonus por rapidez)
                if es_correcta and tiempo_respuesta:
                    if tiempo_respuesta < 5:
                        puntos_obtenidos = puntos_base * 2
                    elif tiempo_respuesta < 10:
                        puntos_obtenidos = int(puntos_base * 1.5)
                    else:
                        puntos_obtenidos = puntos_base

                print(f"   {'✅ Correcta' if es_correcta else '❌ Incorrecta'} - Puntos: {puntos_obtenidos}")

        # Obtener ID de respuesta correcta para mostrar en frontend
        cursor.execute("""
            SELECT idRespuestas FROM RESPUESTAS
            WHERE idPregunta = %s AND esCorrecta = 1
            LIMIT 1
        """, (id_pregunta,))

        respuesta_correcta = cursor.fetchone()
        if respuesta_correcta:
            id_respuesta_correcta = respuesta_correcta[0]

        # Guardar la respuesta (crear tabla si no existe)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RESPUESTA_PARTICIPANTE (
                idRespuestaParticipante BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                idParticipante BIGINT UNSIGNED NOT NULL,
                idPregunta BIGINT UNSIGNED NOT NULL,
                idRespuesta BIGINT UNSIGNED DEFAULT NULL,
                esCorrecta TINYINT(1) DEFAULT 0,
                tiempoRespuesta INT DEFAULT NULL,
                puntosObtenidos INT DEFAULT 0,
                fechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (idParticipante) REFERENCES PARTICIPANTE(idParticipante)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (idPregunta) REFERENCES PREGUNTAS(idPregunta)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            INSERT INTO RESPUESTA_PARTICIPANTE
            (idParticipante, idPregunta, idRespuesta, esCorrecta, tiempoRespuesta, puntosObtenidos)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id_participante, id_pregunta, id_respuesta, es_correcta, tiempo_respuesta, puntos_obtenidos))

        id_respuesta_guardada = cursor.lastrowid
        print(f"✅ Respuesta guardada en BD con ID: {id_respuesta_guardada}")

        # Actualizar estadísticas del participante
        cursor.execute("""
            UPDATE PARTICIPANTE
            SET preguntasAcertadas = preguntasAcertadas + %s,
                puntajeFinal = puntajeFinal + %s
            WHERE idParticipante = %s
        """, (1 if es_correcta else 0, puntos_obtenidos, id_participante))

        print(f"✅ Estadísticas del participante actualizadas\n")

        conexion.commit()

        return jsonify({
            'success': True,
            'es_correcta': es_correcta,
            'puntos_obtenidos': puntos_obtenidos,
            'id_respuesta_correcta': id_respuesta_correcta
        })

    except Exception as e:
        print(f"❌ Error al guardar respuesta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/iniciar-juego', methods=['POST'])
def iniciar_juego():
    """Inicia el juego y notifica a todos los participantes"""
    data = request.get_json()
    pin = data.get('pin', '').replace(' ', '')
    id_cuestionario = data.get('id_cuestionario')

    if not pin:
        return jsonify({'error': 'PIN requerido'}), 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Actualizar estado de la sesión a "en_progreso" y resetear pregunta_actual a 1
        cursor.execute("""
            UPDATE SESION_JUEGO
            SET estado = 'en_progreso', pregunta_actual = 1
            WHERE pin = %s AND estado = 'esperando'
        """, (pin,))

        conexion.commit()

        # Actualizar también en la memoria (salas_espera)
        if pin in salas_espera:
            salas_espera[pin]['estado'] = 'en_progreso'

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error al iniciar juego: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/estado-juego/<int:id_sesion>')
def estado_juego(id_sesion):
    """Devuelve el estado actual del juego (pregunta actual, estado)"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            SELECT estado, pregunta_actual
            FROM SESION_JUEGO
            WHERE idSesion = %s
        """, (id_sesion,))

        sesion = cursor.fetchone()

        if not sesion:
            return jsonify({"error": "Sesión no encontrada"}), 404

        return jsonify({
            "success": True,
            "estado": sesion[0],
            "pregunta_actual": sesion[1] or 1
        })

    except Exception as e:
        print(f"Error al obtener estado: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/actualizar-pregunta', methods=['POST'])
def actualizar_pregunta():
    """Actualiza el número de pregunta actual (llamado por el creador)"""
    data = request.get_json()
    id_sesion = data.get('id_sesion')
    pregunta_num = data.get('pregunta_num')

    if not id_sesion or not pregunta_num:
        return jsonify({"error": "Datos incompletos"}), 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            UPDATE SESION_JUEGO
            SET pregunta_actual = %s
            WHERE idSesion = %s
        """, (pregunta_num, id_sesion))

        conexion.commit()

        return jsonify({"success": True})

    except Exception as e:
        print(f"Error al actualizar pregunta: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/api/finalizar-juego', methods=['POST'])
def finalizar_juego():
    """Finaliza el juego y calcula ranking final"""
    data = request.get_json()
    id_sesion = data.get('id_sesion')

    if not id_sesion:
        return jsonify({'error': 'ID de sesión requerido'}), 400

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Actualizar estado de la sesión y fecha de fin
        cursor.execute("""
            UPDATE SESION_JUEGO
            SET estado = 'finalizado',
                fechaHoraFin = NOW()
            WHERE idSesion = %s
        """, (id_sesion,))

        conexion.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error al finalizar juego: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conexion.close()

@app.route('/ranking_juego')
def ranking_juego():
    """Muestra el ranking final de un juego específico"""
    if 'usuario' not in session:
        return redirect('/login')

    id_sesion = request.args.get('id')

    if not id_sesion:
        flash('ID de sesión no válido', 'error')
        return redirect('/biblioteca')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Obtener información de la sesión
        cursor.execute("""
            SELECT s.idSesion, s.pin, c.titulo, c.idCuestionario,
                   COALESCE(s.fechaHoraInicio, NOW()) as fecha_inicio,
                   s.idUsuarioCreador
            FROM SESION_JUEGO s
            JOIN CUESTIONARIO c ON s.idCuestionario = c.idCuestionario
            WHERE s.idSesion = %s
        """, (id_sesion,))

        sesion = cursor.fetchone()

        if not sesion:
            flash('Sesión no encontrada', 'error')
            return redirect('/biblioteca')

        # Verificar si el usuario actual es el creador
        es_creador = (sesion[5] == session.get('id_usuario'))

        # Obtener ranking de participantes
        cursor.execute("""
            SELECT
                p.nickName,
                p.puntajeFinal,
                p.preguntasAcertadas,
                COUNT(DISTINCT rp.idPregunta) as total_respondidas
            FROM PARTICIPANTE p
            LEFT JOIN RESPUESTA_PARTICIPANTE rp ON p.idParticipante = rp.idParticipante
            WHERE p.idSesion = %s
            GROUP BY p.idParticipante
            ORDER BY p.puntajeFinal DESC, p.preguntasAcertadas DESC
        """, (id_sesion,))

        participantes = cursor.fetchall()

        ranking = []
        for idx, p in enumerate(participantes, 1):
            ranking.append({
                'posicion': idx,
                'nombre': p[0],
                'puntos': p[1],
                'aciertos': p[2],
                'total_respondidas': p[3]
            })

        return render_template('ranking_final.html',
                             titulo=sesion[2],
                             pin=sesion[1],
                             fecha=sesion[4],
                             id_cuestionario=sesion[3],
                             es_creador=es_creador,
                             ranking=ranking)

    except Exception as e:
        print(f"Error en ranking_juego: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al cargar el ranking', 'error')
        return redirect('/biblioteca')
    finally:
        cursor.close()
        conexion.close()

# ============================================
# RUTA DE RANKING GENERAL (Histórico)
# ============================================
@app.route('/ranking')
def ranking_general():
    """Muestra el ranking histórico de todos los juegos"""
    return render_template('ranking_general.html')

# NOTA: La ruta /ranking_final no es necesaria porque ranking_final.html
# se renderiza desde /ranking_juego después de finalizar una partida.
# Si necesitas acceso directo, descomenta lo siguiente:
# @app.route('/ranking_final')
# def ranking_final():
#     return render_template('ranking_final.html')

# ============================================
# RUTAS DE ADMINISTRACIÓN - ROLES
# ============================================
@app.route('/roles')
def listar_roles():
    roles = controlador_roles.obtener_roles()
    return render_template('roles.html', roles=roles)

@app.route('/roles/agregar')
def agregar_rol():
    return render_template('agregar_rol.html')

@app.route('/roles/guardar', methods=['POST'])
def guardar_rol():
    nombre = request.form['nombre']
    if controlador_roles.insertar_rol(nombre):
        flash('Rol agregado exitosamente.', 'success')
    else:
        flash('Error: El rol ya existe o no se pudo guardar.', 'error')
    return redirect(url_for('listar_roles'))

@app.route('/roles/editar/<int:idRol>')
def editar_rol(idRol):
    rol = controlador_roles.obtener_rol_por_id(idRol)
    if not rol:
        flash('Rol no encontrado.', 'error')
        return redirect(url_for('listar_roles'))
    return render_template('editar_rol.html', rol=rol)

@app.route('/roles/actualizar/<int:idRol>', methods=['POST'])
def actualizar_rol(idRol):
    nombre_nuevo = request.form['nombre']
    if controlador_roles.actualizar_rol(idRol, nombre_nuevo):
        flash('Rol actualizado exitosamente.', 'success')
    else:
        flash('Error al actualizar el rol. El nombre podría ya existir.', 'error')
    return redirect(url_for('listar_roles'))

@app.route('/roles/eliminar/<int:idRol>')
def eliminar_rol(idRol):
    if controlador_roles.eliminar_rol(idRol):
        flash('Rol eliminado exitosamente.', 'success')
    else:
        flash('Error al eliminar el rol.', 'error')
    return redirect(url_for('listar_roles'))

# ============================================
# RUTAS DE ADMINISTRACIÓN - LUGARES DE TRABAJO
# ============================================
@app.route('/lugares_trabajo')
def listar_lugares_trabajo():
    lugares = controlador_lugares_trabajo.obtener_lugares_trabajo()
    return render_template('lugar_trabajo.html', lugares=lugares)

@app.route('/lugares_trabajo/agregar')
def agregar_lugar_trabajo():
    return render_template('agregar_lugar_trabajo.html')

@app.route('/lugares_trabajo/guardar', methods=['POST'])
def guardar_lugar_trabajo():
    nombreLugar = request.form['nombreLugar']
    dominio = request.form['dominio']
    if controlador_lugares_trabajo.insertar_lugar_trabajo(nombreLugar, dominio):
        flash('Lugar de trabajo agregado exitosamente.', 'success')
    else:
        flash('Error: El nombre o dominio ya existen, o no se pudo guardar.', 'error')
    return redirect(url_for('listar_lugares_trabajo'))

@app.route('/lugares_trabajo/editar/<int:idLugar>')
def editar_lugar_trabajo(idLugar):
    lugar = controlador_lugares_trabajo.obtener_lugar_trabajo_por_id(idLugar)
    if not lugar:
        flash('Lugar no encontrado.', 'error')
        return redirect(url_for('listar_lugares_trabajo'))
    return render_template('editar_lugar_trabajo.html', lugar=lugar)

@app.route('/lugares_trabajo/actualizar/<int:idLugar>', methods=['POST'])
def actualizar_lugar_trabajo(idLugar):
    nuevo_nombre = request.form['nombreLugar']
    nuevo_dominio = request.form['dominio']
    if controlador_lugares_trabajo.actualizar_lugar_trabajo(idLugar, nuevo_nombre, nuevo_dominio):
        flash('Lugar actualizado exitosamente.', 'success')
    else:
        flash('Error al actualizar el lugar. El nombre o dominio podrían ya existir.', 'error')
    return redirect(url_for('listar_lugares_trabajo'))

@app.route('/lugares_trabajo/eliminar/<int:idLugar>')
def eliminar_lugar_trabajo(idLugar):
    if controlador_lugares_trabajo.eliminar_lugar_trabajo(idLugar):
        flash('Lugar eliminado exitosamente.', 'success')
    else:
        flash('Error al eliminar el lugar.', 'error')
    return redirect(url_for('listar_lugares_trabajo'))

# ============================================
# RUTAS DE ADMINISTRACIÓN - TIPOS DE PREGUNTA
# ============================================
@app.route('/tipos_pregunta')
def listar_tipos_pregunta():
    tipos = controlador_tipo_preguntas.obtener_tipos_pregunta()
    return render_template('tipo_pregunta.html', tipos=tipos)

@app.route('/tipos_pregunta/agregar')
def agregar_tipo_pregunta():
    return render_template('agregar_tipo_pregunta.html')

@app.route('/tipos_pregunta/guardar', methods=['POST'])
def guardar_tipo_pregunta():
    nombreTipoPregunta = request.form['nombreTipoPregunta']
    if controlador_tipo_preguntas.insertar_tipo_pregunta(nombreTipoPregunta):
        flash('Tipo de pregunta agregado exitosamente.', 'success')
    else:
        flash('Error: El tipo ya existe o no se pudo guardar.', 'error')
    return redirect(url_for('listar_tipos_pregunta'))

@app.route('/tipos_pregunta/editar/<int:idTipoPregunta>')
def editar_tipo_pregunta(idTipoPregunta):
    tipo = controlador_tipo_preguntas.obtener_tipo_pregunta_por_id(idTipoPregunta)
    if not tipo:
        flash('Tipo de pregunta no encontrado.', 'error')
        return redirect(url_for('listar_tipos_pregunta'))
    return render_template('editar_tipo_pregunta.html', tipo=tipo)

@app.route('/tipos_pregunta/actualizar/<int:idTipoPregunta>', methods=['POST'])
def actualizar_tipo_pregunta(idTipoPregunta):
    nuevo_nombre = request.form['nombreTipoPregunta']
    if controlador_tipo_preguntas.actualizar_tipo_pregunta(idTipoPregunta, nuevo_nombre):
        flash('Tipo de pregunta actualizado exitosamente.', 'success')
    else:
        flash('Error al actualizar el tipo de pregunta. El nombre podría ya existir.', 'error')
    return redirect(url_for('listar_tipos_pregunta'))

@app.route('/tipos_pregunta/eliminar/<int:idTipoPregunta>')
def eliminar_tipo_pregunta(idTipoPregunta):
    if controlador_tipo_preguntas.eliminar_tipo_pregunta(idTipoPregunta):
        flash('Tipo de pregunta eliminado exitosamente.', 'success')
    else:
        flash('Error al eliminar el tipo de pregunta.', 'error')
    return redirect(url_for('listar_tipos_pregunta'))


# ============================================
# RUTA PARA INGRESAR CÓDIGO SIN INICIAR SESIÓN
# ============================================
@app.route('/ingresar_codigo', methods=['GET'])
def ingresar_codigo():
    return render_template('ingresar_codigo_sin_login.html')

@app.route('/validar_codigo', methods=['POST'])
def validar_codigo():
    codigo = request.form.get('codigo', '').strip()

    if not codigo:
        flash('Por favor ingresa un código válido.', 'error')
        return redirect(url_for('ingresar_codigo'))

    # Aquí puedes validar el código en BD, por ejemplo:
    # valido = controlador_cuestionarios.validar_codigo(codigo)
    # if not valido:
    #     flash('El código no existe o ha expirado.', 'error')
    #     return redirect(url_for('ingresar_codigo'))

    # Si todo está bien, redirigir a sala de espera o cuestionario:
    return redirect(url_for('salaEspera'))

# @app.route('/cuestionario/<int:cuestionario_id>/responder')
# def responder_cuestionario(cuestionario_id):
#     cuestionario = obtener_cuestionario_por_id(cuestionario_id)
#     return render_template('cuestionario_responder.html', cuestionario=cuestionario)

# ============================================
# EJECUTAR APLICACIÓN
# ============================================
if __name__ == '__main__':
    app.run(debug=True)