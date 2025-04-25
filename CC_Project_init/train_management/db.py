import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="host.docker.internal",
        user="root",
        password="mithun0611",
        database="train_db",
        port = 3306  # Update with your MySQL port if different
    )
