import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env file

dbpassword = os.getenv('DB_PASSWORD')  # Use parentheses, not brackets

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="greenkerala",
        user="postgres",
        password=dbpassword
    )
