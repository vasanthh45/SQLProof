import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

connection = None

try:
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    if connection.is_connected():
        print("SQLProof connected to MySQL successfully!")
        print("Database:", connection.database)

finally:
    if connection and connection.is_connected():
        connection.close()
        print("Database connection closed.")