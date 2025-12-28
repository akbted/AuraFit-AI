import psycopg2
import os
from app.config.settings import setting

class DBManger:
    def __init__(self):
        self.user = setting.DB_USER
        self.password = setting.DB_PASSWORD
        self.host = setting.DB_HOST
        self.port = setting.DB_PORT
        self.dbname = setting.DB_NAME
        self.connection = None

    def db_connection_test(self):
        try:
            self.connection = psycopg2.connect(
                user = self.user,
                password = self.password,
                host = self.host,
                port = self.port,
                dbname = self.dbname
            )
            print("Connect successful!")

            if self.connection:
                cursor = self.connection.cursor()

                # Example 
                cursor.execute("SELECT NOW();")
                result = cursor.fetchone()
                print("Current Time:", result)

                # Closing the Cursor
                cursor.close()
        except Exception as e:
            raise Exception("Connection Failed!")
        
    def close_connection(self):
        try:
            if self.connection:
                self.connection.close()
                print("Connection closed.")

        except Exception as e:
            print(f"Failed to close connection: {e}")

    def create_tables(self):
        try:
            pass 
        except Exception as e:
            print(f"Failed to create tables: {e}")

    def drop_tables(self, table_name):
        try:
            pass 
        except Exception as e:
            print(f"Failed to drop tables: {e}")

    def migrate(self):
        try:
            pass 
        except Exception as e:
            print(f"Failed to migrate: {e}")


if __name__ == "__main__":
    db_init = DBManger()

    # Testing DB Connection
    db_init.db_connection_test()

    # Closing the DB Connection
    db_init.close_connection()