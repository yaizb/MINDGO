from bd import obtener_conexion

def insertar_rol(nombre):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idRol FROM rol WHERE nombre = %s", (nombre,))
            if cursor.fetchone():
                print(f"El rol '{nombre}' ya existe.")
                return False
            cursor.execute("INSERT INTO rol(nombre) VALUES (%s)", (nombre,))
            conexion.commit()
            return True
    except Exception as e:
        print(f"Ocurrió un error al insertar el rol: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

def obtener_roles():
    conexion = obtener_conexion()
    roles = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idRol, nombre FROM rol")
            roles = cursor.fetchall()
    except Exception as e:
        print(f"Ocurrió un error al obtener los roles: {e}")
    finally:
        conexion.close()
    return roles

def obtener_rol_por_id(idRol):
    conexion = obtener_conexion()
    rol = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idRol, nombre FROM rol WHERE idRol = %s", (idRol,))
            rol = cursor.fetchone()
    except Exception as e:
        print(f"Ocurrió un error al obtener el rol por ID: {e}")
    finally:
        conexion.close()
    return rol

def eliminar_rol(idRol):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM rol WHERE idRol = %s", (idRol,))
            if cursor.rowcount > 0:
                conexion.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ocurrió un error al eliminar el rol: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

def actualizar_rol(idRol, nuevo_nombre):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Opcional: Verificar que el nuevo nombre no exista ya en otro rol
            cursor.execute("SELECT idRol FROM rol WHERE nombre = %s AND idRol != %s", (nuevo_nombre, idRol))
            if cursor.fetchone():
                return False

            cursor.execute("UPDATE rol SET nombre = %s WHERE idRol = %s", (nuevo_nombre, idRol))
            conexion.commit()
            return True
    except Exception as e:
        print(f"Ocurrió un error al actualizar el rol: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()