from mysql.connector import MySQLConnection, Error
from mysql.connector.plugins import mysql_native_password, caching_sha2_password
import logging
import pathlib
from pathlib import Path
from Common import get_config
import os

# logging
logger = logging.getLogger("TelegramBot_MySql")
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d, %(name)s, %(levelname)s: %(message)s',
                              '%Y-%m-%d %H:%M:%S')

path_config = Path(pathlib.Path.cwd(), "logs", logger.name + ".log")
file_log = logging.FileHandler(filename=path_config, mode="w")
file_log.setFormatter(formatter)
logger.addHandler(file_log)

console_out = logging.StreamHandler()
console_out.setFormatter(formatter)
logger.addHandler(console_out)

class MySqlCall:
    def __init__(self):
        # mysql
        user = get_config("mysql", "user")
        password = get_config("mysql", "password")
        host = get_config("mysql", "host")
        database = get_config("mysql", "database")

        self.param = {
          'user': user,
          'password': password,
          'host': host,
          'database': database,
          'raise_on_warnings': False,
          'auth_plugin': 'mysql_native_password'
        }

        self.conn = None
        self.cursor = None

    def start_conn(self):
        try:
            self.conn = MySQLConnection(**self.param, autocommit=True)
            self.cursor = self.conn.cursor()

            logger.debug(f"Connection is Started")
            # print(f"Connection is Started")

        except Error as e:
            logger.error(f"e start_conn: {e}")
        except Exception as ex:
            logger.error(f"ex start_conn: {ex}")

    def stop_conn(self):
        try:
            self.cursor.close()
            self.conn.close()
        except Error as e:
            logger.error(f"stop_conn: {e}")

    def get_image(self, brief):
        sql = f"select image from image where brief ='{brief}'"
        self.cursor.execute(sql)
        row = self.cursor.fetchone()

        logger.info(row[0])

        return row[0]

    def get_status(self):
        sql = "select xml from status order by datetime desc limit 1"
        self.cursor.execute(sql)
        row = self.cursor.fetchone()

        logger.info(row[0])

        return row[0]

    def subscribe(self, user_id, first_name, last_name, username, unsubscribe):
        arg = (user_id, first_name, last_name, username, unsubscribe)
        self.cursor.callproc("telegram_subscribe", arg)

    def get_subscribes(self):
        sql = "SELECT user_id FROM telegram_subscribes where unsubscribe = 0"
        self.cursor.execute(sql)

        subscribes = []
        result = self.cursor.fetchall()

        for row in result:
            subscribes.append(row[0])

        return subscribes


if __name__ == "__main__":
    db = MySqlCall()
    db.start_conn()

    db.get_status()
    logger.info("row[0]")
    # db.load_image("canvas")

    print(os.path.basename(__file__))
   # print(os.path.dirname(current_file))

    db.stop_conn()
