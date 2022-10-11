from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

class Database:
    username=os.getenv('DB_USER')
    password=os.getenv('DB_PASSWORD')
    db=os.getenv('DB_NAME')
    host=os.getenv('DB_HOST')
    port=os.getenv('DB_PORT')
    url: str 
    
    def __init__(self):
        self.url = f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}/{self.db}"
    
    def get_engine(self):
        return create_engine(self.url)

    def get_connection(self): 
        return self.get_engine().connect()    

    def get_data(self, table_name):
        with self.get_connection() as connection:
            return connection.execute(f"SELECT * FROM {table_name}").fetchall()

    