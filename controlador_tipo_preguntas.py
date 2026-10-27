from bd import obtener_conexion

def insertar_tipo_pregunta(nombreTipoPregunta):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idTipoPregunta FROM tipo_pregunta WHERE nombreTipoPregunta = %s", (nombreTipoPregunta,))
            if cursor.fetchone():
                print(f"El tipo de pregunta '{nombreTipoPregunta}' ya existe.")
                return False
            cursor.execute("INSERT INTO tipo_pregunta(nombreTipoPregunta) VALUES (%s)", (nombreTipoPregunta,))
            conexion.commit()
            return True
    except Exception as e:
        print(f"Ocurrió un error al insertar el tipo de pregunta: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

def obtener_tipos_pregunta():
    conexion = obtener_conexion()
    tipos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idTipoPregunta, nombreTipoPregunta FROM tipo_pregunta")
            tipos = cursor.fetchall()
    except Exception as e:
        print(f"Ocurrió un error al obtener los tipos de pregunta: {e}")
    finally:
        conexion.close()
    return tipos

def obtener_tipo_pregunta_por_id(idTipoPregunta):
    conexion = obtener_conexion()
    tipo = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idTipoPregunta, nombreTipoPregunta FROM tipo_pregunta WHERE idTipoPregunta = %s", (idTipoPregunta,))
            tipo = cursor.fetchone()
    except Exception as e:
        print(f"Ocurrió un error al obtener el tipo de pregunta por ID: {e}")
    finally:
        conexion.close()
    return tipo

def eliminar_tipo_pregunta(idTipoPregunta):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM tipo_pregunta WHERE idTipoPregunta = %s", (idTipoPregunta,))
            if cursor.rowcount > 0:
                conexion.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ocurrió un error al eliminar el tipo de pregunta: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

def actualizar_tipo_pregunta(idTipoPregunta, nuevo_nombreTipoPregunta):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idTipoPregunta FROM tipo_pregunta WHERE nombreTipoPregunta = %s AND idTipoPregunta != %s", (nuevo_nombreTipoPregunta, idTipoPregunta))
            if cursor.fetchone():
                return False
            cursor.execute("UPDATE tipo_pregunta SET nombreTipoPregunta = %s WHERE idTipoPregunta = %s", (nuevo_nombreTipoPregunta, idTipoPregunta))
            conexion.commit()
            return True
    except Exception as e:
        print(f"Ocurrió un error al actualizar el tipo de pregunta: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()
