import pymysql

HOST = 'mindgo.mysql.pythonanywhere-services.com'
USER = 'mindgo'
PASSWORD = 'lavacalolamu'
DB = 'mindgo$bd'


def obtener_conexion(con_dict=False):
    if con_dict:
        clasecursor = pymysql.cursors.DictCursor
    else:
        clasecursor = pymysql.cursors.Cursor
    return pymysql.connect(
        host='localhost',
        port=3327,
        user='root',
        password='',
        database='bd_mindgo',
        cursorclass=clasecursor
    )
