import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def obtener_conexion(con_dict=False):
    if con_dict:
        clasecursor = pymysql.cursors.DictCursor
    else:
        clasecursor = pymysql.cursors.Cursor

    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        cursorclass=clasecursor
    )