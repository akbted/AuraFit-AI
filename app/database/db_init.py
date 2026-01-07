import psycopg2
import os
from app.config.settings import setting
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/db_logs.log"), # Writes to a file
        logging.StreamHandler()         # Also prints to console
    ]
)

class DBManger:
    def __init__(self):
        self.user = setting.DB_USER
        self.password = setting.DB_PASSWORD
        self.host = setting.DB_HOST
        self.port = setting.DB_PORT
        self.dbname = setting.DB_NAME
        self.connection = None
        self.schemas = setting.DB_SCHEMA
        self.db_create_connection()

    def db_create_connection(self):
        try:
            self.connection = psycopg2.connect(
                user = self.user,
                password = self.password,
                host = self.host,
                port = self.port,
                dbname = self.dbname
            )
            logging.info("Connect successful!")
        except Exception as e:
            raise Exception("Connection Failed!")

    def db_connection_test(self):
        try:
            self.connection = psycopg2.connect(
                user = self.user,
                password = self.password,
                host = self.host,
                port = self.port,
                dbname = self.dbname
            )
            logging.info("Connect successful!")

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
                logging.info("Connection closed.")

        except Exception as e:
            print(f"Failed to close connection: {e}")

    def create_tables(self):
        try:
            # List all the schemas
            logging.info(f"List of Schemas: {os.listdir(self.schemas)}")
            list_schema_path = [os.path.abspath(os.path.join(self.schemas, item)) for item in os.listdir(self.schemas)]
            for schema in list_schema_path:
                with open(os.path.abspath(schema), "r") as f:
                    sql = f.read()
                    cursor = self.connection.cursor()
                    cursor.execute(sql)
                    self.connection.commit()
                    cursor.close()
            logging.info(msg=f"Created tables based on {os.listdir(self.schemas)}")

        except Exception as e:
            logging.info(f"Failed to create tables: {e}")

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

    def db_connection(self):
        try:
            self.db_create_connection()
            return self.connection
        except Exception as e:
            logging.error("DB Connection Failed!")




if __name__ == "__main__":
    db_init = DBManger()

    # Testing DB Connection
    db_init.db_connection_test()

    # Creating Tables
    db_init.create_tables()

    # Closing the DB Connection
    db_init.close_connection()