from bd import obtener_conexion
import json
import pandas as pd
import os


def crear_cuestionario(titulo, id_usuario, descripcion=''):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO CUESTIONARIO (titulo, idUsuario, fechaHoraCreacion, estado, descripcion)
                   VALUES (%s, %s, NOW(), 'borrador', %s)""",
                (titulo, id_usuario, descripcion)
            )
            conexion.commit()
            return cursor.lastrowid
    finally:
        conexion.close()




def actualizar_cuestionario(id_cuestionario, titulo, descripcion=''):
    """Actualiza el título y descripción de un cuestionario"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """UPDATE CUESTIONARIO
                   SET titulo = %s, descripcion = %s, estado = 'publicado'
                   WHERE idCuestionario = %s""",
                (titulo, descripcion, id_cuestionario)
            )
            conexion.commit()
    finally:
        conexion.close()

def guardar_pregunta(id_cuestionario, numero_pregunta, texto_pregunta, tipo_pregunta,
                     tiempo_limite, puntos, opciones, url_multimedia=None):
    """Guarda una pregunta con sus opciones"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Mapear tipo de pregunta del frontend a la base de datos
            tipo_map = {
                'quiz': 'Selección Simple',
                'verdadero_falso': 'Selección Simple',
                'seleccion_multiple': 'Selección Múltiple'
            }
            tipo_bd = tipo_map.get(tipo_pregunta, 'Selección Simple')

            # Obtener el ID del tipo de pregunta
            cursor.execute("SELECT idTipoPregunta FROM TIPO_PREGUNTA WHERE nombre = %s", (tipo_bd,))
            tipo_result = cursor.fetchone()
            id_tipo_pregunta = tipo_result[0] if tipo_result else 1

            # Insertar pregunta
            cursor.execute(
                """INSERT INTO PREGUNTAS(descripcion, ordenInterno, limiteTiempo, puntos,
                   urlMultimedia, idTipoPregunta, idCuestionario)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (texto_pregunta, numero_pregunta, tiempo_limite, puntos,
                 url_multimedia, id_tipo_pregunta, id_cuestionario)
            )
            id_pregunta = cursor.lastrowid

            # Insertar opciones
            for idx, opcion in enumerate(opciones):
                # Obtener el ID del formato según el color
                color = opcion.get('color', 'Azul').replace('btn-', '').capitalize()
                cursor.execute("SELECT idFormato FROM FORMATO_RESPUESTA WHERE color = %s", (color,))
                formato_result = cursor.fetchone()
                id_formato = formato_result[0] if formato_result else 1

                cursor.execute(
                    """INSERT INTO RESPUESTAS(descripcion, esCorrecta, idPregunta, idFormato)
                       VALUES (%s, %s, %s, %s)""",
                    (opcion['texto'], opcion['es_correcta'], id_pregunta, id_formato)
                )

            conexion.commit()
            return id_pregunta
    finally:
        conexion.close()

def actualizar_pregunta(id_pregunta, texto_pregunta, tipo_pregunta, tiempo_limite,
                       puntos, opciones, url_multimedia=None):
    """Actualiza una pregunta existente"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Mapear tipo de pregunta del frontend a la base de datos
            tipo_map = {
                'quiz': 'Selección Simple',
                'verdadero_falso': 'Selección Simple',
                'seleccion_multiple': 'Selección Múltiple'
            }
            tipo_bd = tipo_map.get(tipo_pregunta, 'Selección Simple')

            # Obtener el ID del tipo de pregunta
            cursor.execute("SELECT idTipoPregunta FROM TIPO_PREGUNTA WHERE nombre = %s", (tipo_bd,))
            tipo_result = cursor.fetchone()
            id_tipo_pregunta = tipo_result[0] if tipo_result else 1

            # Actualizar pregunta
            cursor.execute(
                """UPDATE PREGUNTAS SET descripcion = %s, limiteTiempo = %s,
                   puntos = %s, urlMultimedia = %s, idTipoPregunta = %s WHERE idPregunta = %s""",
                (texto_pregunta, tiempo_limite, puntos, url_multimedia, id_tipo_pregunta, id_pregunta)
            )

            # Eliminar opciones antiguas
            cursor.execute("DELETE FROM RESPUESTAS WHERE idPregunta = %s", (id_pregunta,))

            # Insertar nuevas opciones
            for idx, opcion in enumerate(opciones):
                color = opcion.get('color', 'Azul')
                cursor.execute("SELECT idFormato FROM FORMATO_RESPUESTA WHERE color = %s", (color,))
                formato_result = cursor.fetchone()
                id_formato = formato_result[0] if formato_result else (idx % 4) + 1

                cursor.execute(
                    """INSERT INTO RESPUESTAS(descripcion, esCorrecta, idPregunta, idFormato)
                       VALUES (%s, %s, %s, %s)""",
                    (opcion['texto'], opcion['es_correcta'], id_pregunta, id_formato)
                )

            conexion.commit()
    finally:
        conexion.close()

def obtener_cuestionario(id_cuestionario):
    """Obtiene un cuestionario con todas sus preguntas y opciones"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Obtener cuestionario
            cursor.execute(
                "SELECT * FROM CUESTIONARIO WHERE idCuestionario = %s",
                (id_cuestionario,)
            )
            cuestionario = cursor.fetchone()

            if not cuestionario:
                return None

            # Obtener preguntas
            cursor.execute(
                """SELECT * FROM PREGUNTAS WHERE idCuestionario = %s
                   ORDER BY ordenInterno""",
                (id_cuestionario,)
            )
            preguntas = cursor.fetchall()

            # Obtener opciones para cada pregunta
            preguntas_con_opciones = []
            for pregunta in preguntas:
                cursor.execute(
                    """SELECT * FROM RESPUESTAS WHERE idPregunta = %s""",
                    (pregunta[0],)
                )
                opciones = cursor.fetchall()
                preguntas_con_opciones.append({
                    'pregunta': pregunta,
                    'opciones': opciones
                })

            return {
                'cuestionario': cuestionario,
                'preguntas': preguntas_con_opciones
            }
    finally:
        conexion.close()

def obtener_cuestionarios_usuario(id_usuario):
    """Obtiene todos los cuestionarios de un usuario"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Primero verificar si las columnas existen, si no, agregarlas
            try:
                cursor.execute("SELECT esFavorito, enPapelera FROM CUESTIONARIO LIMIT 1")
            except:
                # Agregar columnas si no existen
                try:
                    cursor.execute("ALTER TABLE CUESTIONARIO ADD COLUMN esFavorito TINYINT(1) DEFAULT 0")
                    cursor.execute("ALTER TABLE CUESTIONARIO ADD COLUMN enPapelera TINYINT(1) DEFAULT 0")
                    conexion.commit()
                except:
                    pass  # Las columnas ya existen o hay otro error

            cursor.execute(
                """SELECT c.idCuestionario, c.titulo, c.descripcion, c.fechaHoraCreacion,
                   COUNT(DISTINCT p.idPregunta) as num_preguntas,
                   COALESCE(c.esFavorito, 0) as esFavorito,
                   COALESCE(c.enPapelera, 0) as enPapelera,
                   (SELECT COUNT(*) FROM SESION_JUEGO s
                    WHERE s.idCuestionario = c.idCuestionario
                    AND s.estado = 'finalizado') as num_completados,
                   (SELECT MAX(s.fechaHoraInicio) FROM SESION_JUEGO s
                    WHERE s.idCuestionario = c.idCuestionario
                    AND s.estado = 'finalizado') as ultima_vez_jugado
                   FROM CUESTIONARIO c
                   LEFT JOIN PREGUNTAS p ON c.idCuestionario = p.idCuestionario
                   WHERE c.idUsuario = %s
                   GROUP BY c.idCuestionario, c.esFavorito, c.enPapelera
                   ORDER BY c.esFavorito DESC, c.fechaHoraCreacion DESC""",
                (id_usuario,)
            )
            rows = cursor.fetchall()

            # Convertir a lista de diccionarios
            cuestionarios = []
            for row in rows:
                cuestionarios.append({
                    'id': row[0],
                    'titulo': row[1],
                    'descripcion': row[2] if len(row) > 2 else None,
                    'fecha_creacion': row[3].strftime('%Y-%m-%d %H:%M:%S') if len(row) > 3 else None,
                    'num_preguntas': row[4] if len(row) > 4 else 0,
                    'es_favorito': bool(row[5]) if len(row) > 5 else False,
                    'en_papelera': bool(row[6]) if len(row) > 6 else False,
                    'num_completados': row[7] if len(row) > 7 else 0,
                    'ultima_vez_jugado': row[8].strftime('%Y-%m-%d %H:%M:%S') if len(row) > 8 and row[8] else None
                })

            return cuestionarios
    finally:
        conexion.close()

def eliminar_pregunta(id_pregunta):
    """Elimina una pregunta y sus opciones"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Eliminar opciones
            cursor.execute("DELETE FROM RESPUESTAS WHERE idPregunta = %s", (id_pregunta,))
            # Eliminar pregunta
            cursor.execute("DELETE FROM PREGUNTAS WHERE idPregunta = %s", (id_pregunta,))
            conexion.commit()
    finally:
        conexion.close()

def eliminar_cuestionario(id_cuestionario):
    """Elimina un cuestionario completo"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Obtener IDs de preguntas
            cursor.execute(
                "SELECT idPregunta FROM PREGUNTAS WHERE idCuestionario = %s",
                (id_cuestionario,)
            )
            preguntas = cursor.fetchall()

            # Eliminar opciones de cada pregunta
            for pregunta in preguntas:
                cursor.execute("DELETE FROM RESPUESTAS WHERE idPregunta = %s", (pregunta[0],))

            # Eliminar preguntas
            cursor.execute("DELETE FROM PREGUNTAS WHERE idCuestionario = %s", (id_cuestionario,))

            # Eliminar cuestionario
            cursor.execute("DELETE FROM CUESTIONARIO WHERE idCuestionario = %s", (id_cuestionario,))

            conexion.commit()
    finally:
        conexion.close()

def limpiar_papelera(id_usuario):
    """Elimina todos los cuestionarios en papelera de un usuario"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Obtener IDs de cuestionarios en papelera
            cursor.execute(
                """SELECT idCuestionario FROM CUESTIONARIO
                   WHERE idUsuario = %s AND enPapelera = 1""",
                (id_usuario,)
            )
            cuestionarios = cursor.fetchall()

            eliminados = 0
            for cuestionario in cuestionarios:
                id_cuestionario = cuestionario[0]

                # Obtener IDs de preguntas
                cursor.execute(
                    "SELECT idPregunta FROM PREGUNTAS WHERE idCuestionario = %s",
                    (id_cuestionario,)
                )
                preguntas = cursor.fetchall()

                # Eliminar opciones de cada pregunta
                for pregunta in preguntas:
                    cursor.execute("DELETE FROM RESPUESTAS WHERE idPregunta = %s", (pregunta[0],))

                # Eliminar preguntas
                cursor.execute("DELETE FROM PREGUNTAS WHERE idCuestionario = %s", (id_cuestionario,))

                # Eliminar cuestionario
                cursor.execute("DELETE FROM CUESTIONARIO WHERE idCuestionario = %s", (id_cuestionario,))

                eliminados += 1

            conexion.commit()
            return eliminados
    finally:
        conexion.close()

def toggle_favorito(id_cuestionario, id_usuario):
    """Marca o desmarca un cuestionario como favorito"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Obtener estado actual
            cursor.execute(
                "SELECT COALESCE(esFavorito, 0) FROM CUESTIONARIO WHERE idCuestionario = %s AND idUsuario = %s",
                (id_cuestionario, id_usuario)
            )
            resultado = cursor.fetchone()

            if resultado:
                nuevo_estado = 0 if resultado[0] else 1
                cursor.execute(
                    "UPDATE CUESTIONARIO SET esFavorito = %s WHERE idCuestionario = %s AND idUsuario = %s",
                    (nuevo_estado, id_cuestionario, id_usuario)
                )
                conexion.commit()
                return bool(nuevo_estado)
            return False
    finally:
        conexion.close()

def mover_a_papelera(id_cuestionario, id_usuario):
    """Mueve un cuestionario a la papelera (soft delete)"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE CUESTIONARIO SET enPapelera = 1 WHERE idCuestionario = %s AND idUsuario = %s",
                (id_cuestionario, id_usuario)
            )
            conexion.commit()
            return True
    finally:
        conexion.close()

def restaurar_cuestionario(id_cuestionario, id_usuario):
    """Restaura un cuestionario de la papelera"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE CUESTIONARIO SET enPapelera = 0 WHERE idCuestionario = %s AND idUsuario = %s",
                (id_cuestionario, id_usuario)
            )
            conexion.commit()
            return True
    finally:
        conexion.close()

# ================== IMPORTACIÓN DESDE ARCHIVO (XLSX/XLS/CSV) ==================

def importar_cuestionario_desde_upload(
    ruta_archivo,
    id_usuario,
    id_cuestionario=None,
    titulo_si_crea=None,
    limite_tiempo_def=30,
    puntos_def=1000
):
    """
    Importa preguntas de un archivo .xlsx/.xls/.csv con columnas:
      - Pregunta
      - Respuesta
      - Alternativa A
      - Alternativa B
      - Alternativa C
      - Alternativa D

    Si no se envía id_cuestionario, crea uno nuevo (título = titulo_si_crea o nombre de archivo).
    Todas las preguntas se registran como 'Selección Simple'.
    """
    try:
        extension = os.path.splitext(ruta_archivo)[1].lower()

        if extension in (".xlsx", ".xls"):
            df = pd.read_excel(ruta_archivo)
        elif extension == ".csv":
            df = pd.read_csv(ruta_archivo)
        else:
            return {"estado": "error", "mensaje": "Formato no soportado. Use .xlsx, .xls o .csv."}

        # Validar columnas mínimas
        columnas_requeridas = {"Pregunta", "Respuesta", "Alternativa A", "Alternativa B", "Alternativa C", "Alternativa D"}
        if not columnas_requeridas.issubset(set(df.columns)):
            return {
                "estado": "error",
                "mensaje": "El archivo debe contener las columnas: Pregunta, Respuesta, Alternativa A, Alternativa B, Alternativa C y Alternativa D."
            }

        # Normalización básica
        df = df.fillna("")

        def _norm(s):  # trim + str
            return str(s).strip()

        # Abrir conexión
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                # Obtener idTipoPregunta para 'Selección Simple'
                cursor.execute("SELECT idTipoPregunta FROM TIPO_PREGUNTA WHERE nombre = %s", ("Selección Simple",))
                row_tipo = cursor.fetchone()
                if not row_tipo:
                    return {"estado": "error", "mensaje": "No existe 'Selección Simple' en TIPO_PREGUNTA."}
                id_tipo_simple = row_tipo[0]

                # Crear cuestionario si hace falta
                creado = False
                if not id_cuestionario:
                    titulo = (titulo_si_crea or os.path.basename(ruta_archivo)).rsplit(".", 1)[0].strip()
                    if not titulo:
                        titulo = "Cuestionario importado"

                    cursor.execute(
                        """INSERT INTO CUESTIONARIO (titulo, idUsuario, fechaHoraCreacion, estado, descripcion)
                           VALUES (%s, %s, NOW(), 'borrador', %s)""",
                        (titulo, id_usuario, "")
                    )
                    id_cuestionario = cursor.lastrowid
                    creado = True

                # Utilidad: obtener idFormato por color (con fallback)
                def _id_formato(color_texto):
                    color = _norm(color_texto)
                    cursor.execute("SELECT idFormato FROM FORMATO_RESPUESTA WHERE color = %s", (color,))
                    r = cursor.fetchone()
                    if r:
                        return r[0]
                    # fallback: primer formato
                    cursor.execute("SELECT idFormato FROM FORMATO_RESPUESTA ORDER BY idFormato ASC LIMIT 1")
                    r2 = cursor.fetchone()
                    if not r2:
                        # Si no hay formatos, creamos uno rápido (Azul) para evitar fallos
                        cursor.execute("INSERT INTO FORMATO_RESPUESTA(color, icono) VALUES('Azul', 'icon-a')")
                        return cursor.lastrowid
                    return r2[0]

                # Mapeo A/B/C/D → colores
                colores = ["Azul", "Rojo", "Verde", "Amarillo"]

                preguntas_insertadas = 0
                respuestas_insertadas = 0
                orden_interno = 1  # incremento simple

                for _, fila in df.iterrows():
                    pregunta = _norm(fila["Pregunta"])
                    if not pregunta:
                        continue

                    alternativas = [
                        _norm(fila["Alternativa A"]),
                        _norm(fila["Alternativa B"]),
                        _norm(fila["Alternativa C"]),
                        _norm(fila["Alternativa D"]),
                    ]
                    respuesta = _norm(fila["Respuesta"]).lower()

                    # Insertar pregunta
                    cursor.execute(
                        """INSERT INTO PREGUNTAS (descripcion, ordenInterno, limiteTiempo, puntos, urlMultimedia, idTipoPregunta, idCuestionario)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (pregunta, orden_interno, limite_tiempo_def, puntos_def, None, id_tipo_simple, id_cuestionario)
                    )
                    id_pregunta = cursor.lastrowid
                    preguntas_insertadas += 1
                    orden_interno += 1

                    # Insertar respuestas (A..D)
                    for i, alt_texto in enumerate(alternativas):
                        if not alt_texto:
                            continue
                        es_correcta = (alt_texto.lower() == respuesta)
                        id_formato = _id_formato(colores[i % len(colores)])
                        cursor.execute(
                            """INSERT INTO RESPUESTAS (descripcion, esCorrecta, idPregunta, idFormato)
                               VALUES (%s, %s, %s, %s)""",
                            (alt_texto, 1 if es_correcta else 0, id_pregunta, id_formato)
                        )
                        respuestas_insertadas += 1

                conexion.commit()
                return {
                    "estado": "ok",
                    "creado": creado,
                    "idCuestionario": id_cuestionario,
                    "preguntas": preguntas_insertadas,
                    "respuestas": respuestas_insertadas
                }

        except Exception as e:
            try:
                conexion.rollback()
            except:
                pass
            return {"estado": "error", "mensaje": f"Error al guardar en la base de datos: {e}"}
        finally:
            try:
                conexion.close()
            except:
                pass

    except Exception as e:
        return {"estado": "error", "mensaje": f"Ocurrió un error al procesar el archivo: {e}"}