from bd import obtener_conexion

# Insertar nuevo lugar de trabajo
def insertar_lugar_trabajo(nombreLugar, dominio):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Validar duplicados por nombre o dominio
            cursor.execute(
                "SELECT idLugarTrabajo FROM lugar_trabajo WHERE nombreLugar = %s OR dominio = %s",
                (nombreLugar, dominio)
            )
            if cursor.fetchone():
                print(f"El lugar '{nombreLugar}' o el dominio '{dominio}' ya existen.")
                return False

            cursor.execute(
                "INSERT INTO lugar_trabajo (nombreLugar, dominio) VALUES (%s, %s)",
                (nombreLugar, dominio)
            )
            conexion.commit()
            return True
    except Exception as e:
        print(f"Ocurrió un error al insertar el lugar de trabajo: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

# Obtener todos los lugares de trabajo
def obtener_lugares_trabajo():
    conexion = obtener_conexion()
    lugares = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT idLugarTrabajo, nombreLugar, dominio FROM lugar_trabajo")
            lugares = cursor.fetchall()
    except Exception as e:
        print(f"Ocurrió un error al obtener los lugares de trabajo: {e}")
    finally:
        conexion.close()
    return lugares

# Obtener un lugar por su ID
def obtener_lugar_trabajo_por_id(idLugar):
    conexion = obtener_conexion()
    lugar = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT idLugarTrabajo, nombreLugar, dominio FROM lugar_trabajo WHERE idLugarTrabajo = %s",
                (idLugar,)
            )
            lugar = cursor.fetchone()
    except Exception as e:
        print(f"Ocurrió un error al obtener el lugar de trabajo por ID: {e}")
    finally:
        conexion.close()
    return lugar

# Actualizar un lugar de trabajo existente
def actualizar_lugar_trabajo(idLugar, nuevo_nombre, nuevo_dominio):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Verificar duplicados (excepto el mismo id)
            cursor.execute(
                "SELECT idLugarTrabajo FROM lugar_trabajo WHERE (nombreLugar = %s OR dominio = %s) AND idLugarTrabajo != %s",
                (nuevo_nombre, nuevo_dominio, idLugar)
            )
            if cursor.fetchone():
                print(f"Ya existe otro lugar con el nombre '{nuevo_nombre}' o dominio '{nuevo_dominio}'.")
                return False

            cursor.execute(
                "UPDATE lugar_trabajo SET nombreLugar = %s, dominio = %s WHERE idLugarTrabajo = %s",
                (nuevo_nombre, nuevo_dominio, idLugar)
            )
            conexion.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Ocurrió un error al actualizar el lugar de trabajo: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()

# Eliminar un lugar de trabajo
def eliminar_lugar_trabajo(idLugar):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM lugar_trabajo WHERE idLugarTrabajo = %s", (idLugar,))
            conexion.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Ocurrió un error al eliminar el lugar de trabajo: {e}")
        conexion.rollback()
        return False
    finally:
        conexion.close()