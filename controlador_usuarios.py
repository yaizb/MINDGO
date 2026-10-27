from bd import obtener_conexion

# bd.py (o el archivo donde está obtener_conexion)
import uuid
from datetime import datetime, timedelta

def insertar_usuario_con_token(nombres, apellidos, email, contrasena):
    conexion = obtener_conexion()
    token = str(uuid.uuid4())
    with conexion.cursor() as cursor:
        cursor.execute("SELECT id FROM usuario WHERE email = %s", (email,))
        if cursor.fetchone():
            conexion.close()
            return None  # Email ya existe
        cursor.execute("""
            INSERT INTO usuario(nombres, apellidos, email, contrasena, verificado, token_verificacion)
            VALUES (%s, %s, %s, %s, FALSE, %s)
        """, (nombres, apellidos, email, contrasena, token))
    conexion.commit()
    conexion.close()
    return token

def verificar_usuario(token):
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        cursor.execute("SELECT id FROM usuario WHERE token_verificacion = %s AND verificado = FALSE", (token,))
        usuario = cursor.fetchone()
        if usuario:
            cursor.execute("UPDATE usuario SET verificado = TRUE, token_verificacion = NULL WHERE token_verificacion = %s", (token,))
            conexion.commit()
            conexion.close()
            return True
    conexion.close()
    return False

def obtener_usuario_por_email_y_contrasena(email, contrasena):
    conexion = obtener_conexion(con_dict=True)
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT
                id,
                nombres,
                apellidos,
                email,
                contrasena,
                verificado,
                avatar
            FROM usuario
            WHERE email = %s AND contrasena = %s
        """, (email, contrasena))
        usuario = cursor.fetchone()
    conexion.close()
    return usuario


def generar_token_recuperacion(email):
    try:
        conexion = obtener_conexion()
        token = str(uuid.uuid4())
        expira = datetime.now() + timedelta(hours=1)
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE usuario
                SET token_recuperacion = %s, expira_recuperacion = %s
                WHERE email = %s AND verificado = TRUE
            """, (token, expira, email))
            filas = cursor.rowcount
        conexion.commit()
        conexion.close()
        return token if filas > 0 else None
    except Exception as e:
        print("ERROR en generar_token_recuperacion:", str(e))
        return None

def validar_token_recuperacion(token):
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT email FROM usuario
            WHERE token_recuperacion = %s AND expira_recuperacion > NOW()
        """, (token,))
        resultado = cursor.fetchone()
    conexion.close()
    return resultado[0] if resultado else None

def actualizar_contrasena(email, nueva_contrasena):
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        cursor.execute("""
            UPDATE usuario
            SET contrasena = %s, token_recuperacion = NULL, expira_recuperacion = NULL
            WHERE email = %s
        """, (nueva_contrasena, email))
    conexion.commit()
    conexion.close()

def actualizar_avatar(usuario_id, nuevo_avatar):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE usuario SET avatar = %s WHERE id = %s",
                (nuevo_avatar, usuario_id)
            )
        conexion.commit()
        return True
    except Exception as e:
        print("Error al actualizar avatar:", str(e))
        return False
    finally:
        conexion.close()