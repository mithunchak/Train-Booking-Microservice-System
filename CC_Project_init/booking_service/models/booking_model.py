import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="101010",
        database="booking_service"
    )

def insert_booking(data):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO bookings (
        pnr, train_number, passenger_name, age, gender,
        date_of_journey, from_station, to_station, class_type
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        passenger_data['pnr'],
        data['train_number'],
        data['passenger_name'],
        int(data['age']),
        data['gender'],
        data['date_of_journey'],
        data['from_station'],
        data['to_station'],
        data['class_type']
    ))
    conn.commit()
    conn.close()
