import mysql.connector
from flask import current_app

def get_db():
    if 'db' not in current_app.config:
        current_app.config['db'] = mysql.connector.connect(
            host="host.docker.internal",
            user="root",
            password="mithun0611",  # Update with your MySQL password
            database="train_seat_availability",
            port = 3306  # Update with your MySQL port if different
        )
    return current_app.config['db']
