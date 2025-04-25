from flask import Flask, render_template, request, jsonify
import mysql.connector
import logging
import os
import datetime
import traceback
from db_config import db_config  # Import the config file instead of defining DB_CONFIG inline

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='[PNR SERVICE] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Function to get database connection - similar to booking service
def get_db_connection():
    """Get a connection to the database"""
    return mysql.connector.connect(**db_config)

# API key validation
def validate_api_key(request):
    """Validate the API key from request headers"""
    api_key = request.headers.get('X-API-Key')
    valid_keys = [
        'booking-service-key',
        # Add other service keys as needed
    ]
    return api_key in valid_keys or True  # For testing, always return True

# Home route for input form
@app.route('/')
def home():
    return render_template('index.html')  # Home page with the form

# Submit route for checking PNR
@app.route('/submit', methods=['POST'])
def submit():
    logger.info("Form submitted to /submit ✅")
    pnr_number = request.form['pnr']  # Getting PNR number from form input

    try:
        connection = get_db_connection()  # Using the new function
        cursor = connection.cursor(dictionary=True)  # Use dictionary cursor for easier access
        
        # Check if the table exists
        cursor.execute("SHOW TABLES LIKE 'pnr_status'")
        if not cursor.fetchone():
            logger.error("Table 'pnr_status' does not exist")
            return "Database table 'pnr_status' not found. Please create the required database structure.", 500
        
        # First get the main PNR record
        cursor.execute("SELECT * FROM pnr_status WHERE pnr = %s", (pnr_number,))
        pnr_record = cursor.fetchone()
        
        # Check if PNR exists in the database
        if not pnr_record:
            cursor.close()
            connection.close()
            return "PNR not found.", 404
        
        # Check if the passengers table exists
        cursor.execute("SHOW TABLES LIKE 'pnr_passengers'")
        passengers_table_exists = cursor.fetchone() is not None
        
        passengers = []
        if passengers_table_exists:
            # Now get all passengers associated with this PNR
            cursor.execute("SELECT * FROM pnr_passengers WHERE pnr = %s", (pnr_number,))
            passengers = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Prepare the first passenger for backward compatibility
        first_passenger = passengers[0] if passengers else {"name": "N/A", "age": "N/A", "gender": "N/A", 
                                                         "booking_status": "N/A", "current_status": "N/A"}
        
        return render_template("result.html",
                        pnr=pnr_record['pnr'],
                        name=first_passenger.get('name', 'N/A'),
                        age=first_passenger.get('age', 'N/A'),
                        gender=first_passenger.get('gender', 'N/A'),
                        train_name=pnr_record['train_name'],
                        from_station=pnr_record['from_station'],
                        to_station=pnr_record['to_station'],
                        class_type=pnr_record['class_type'],
                        quota=pnr_record['quota'],
                        boarding_point=pnr_record['boarding_point'],
                        available_seats=pnr_record['available_seats'],
                        doj=pnr_record['doj'],
                        booking_status=first_passenger.get('booking_status', 'N/A'),
                        current_status=first_passenger.get('current_status', 'N/A'),
                        passengers=passengers)  # Pass all passengers for multi-passenger display
        
    except Exception as e:
        logger.error(f"Error in submit route: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error processing request: {str(e)}", 500

# API route to support Booking microservice
@app.route('/api/status/<pnr>', methods=['GET'])
def get_pnr_status(pnr):
    logger.info(f"API call received for PNR: {pnr} ✅")
    
    # Validate API key for service-to-service communication
    if not validate_api_key(request):
        logger.warning(f"Unauthorized API access attempt for PNR: {pnr}")
        return jsonify({'error': 'Unauthorized access'}), 401
    
    try:
        connection = get_db_connection()  # Using the new function
        cursor = connection.cursor(dictionary=True)
        
        # Check if the tables exist
        cursor.execute("SHOW TABLES LIKE 'pnr_status'")
        if not cursor.fetchone():
            logger.error("Table 'pnr_status' does not exist")
            return jsonify({'error': 'Database not properly initialized'}), 500
        
        # Get PNR main record
        cursor.execute("SELECT * FROM pnr_status WHERE pnr = %s", (pnr,))
        pnr_record = cursor.fetchone()
        
        if not pnr_record:
            cursor.close()
            connection.close()
            return jsonify({'error': 'PNR not found'}), 404
        
        # Check if passengers table exists
        cursor.execute("SHOW TABLES LIKE 'pnr_passengers'")
        passengers_table_exists = cursor.fetchone() is not None
        
        passengers = []
        if passengers_table_exists:
            # Get all passengers
            cursor.execute("SELECT * FROM pnr_passengers WHERE pnr = %s", (pnr,))
            passengers = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Prepare the full response with PNR details and all passengers
        response = {
            'pnr': pnr_record['pnr'],
            'train_name': pnr_record['train_name'],
            'from_station': pnr_record['from_station'],
            'to_station': pnr_record['to_station'],
            'class_type': pnr_record['class_type'],
            'quota': pnr_record['quota'],
            'boarding_point': pnr_record['boarding_point'],
            'available_seats': pnr_record['available_seats'],
            'doj': pnr_record['doj'],
            'passengers': passengers
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in get_pnr_status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

@app.route('/api/update_pnr', methods=['POST'])
def update_pnr():
    """API endpoint for the Booking Service to create/update PNR information"""
    logger.info("Received PNR update request")
    
    # Validate API key for service-to-service communication
    if not validate_api_key(request):
        logger.warning("Unauthorized API access attempt for PNR update")
        return jsonify({'error': 'Unauthorized access'}), 401
    
    data = request.get_json()
    logger.info(f"Received data: {data}")
    
    if not data or 'pnr' not in data:
        return jsonify({'error': 'Invalid data format'}), 400
    
    try:
        connection = get_db_connection()  # Using the new function
        cursor = connection.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pnr_status (
                pnr VARCHAR(20) PRIMARY KEY,
                train_name VARCHAR(100) NOT NULL,
                from_station VARCHAR(100) NOT NULL,
                to_station VARCHAR(100) NOT NULL,
                class_type VARCHAR(20) NOT NULL,
                quota VARCHAR(20) NOT NULL,
                boarding_point VARCHAR(100) NOT NULL,
                available_seats VARCHAR(20) NOT NULL,
                doj DATE NOT NULL,
                last_updated DATETIME NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pnr_passengers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pnr VARCHAR(20) NOT NULL,
                passenger_number INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                age INT NOT NULL,
                gender VARCHAR(10) NOT NULL,
                booking_status VARCHAR(20) NOT NULL,
                current_status VARCHAR(10) NOT NULL
            )
        """)
        
        # Check if PNR already exists
        cursor.execute("SELECT pnr FROM pnr_status WHERE pnr = %s", (data['pnr'],))
        existing_pnr = cursor.fetchone()
        
        if existing_pnr:
            # Update existing PNR record
            cursor.execute("""
                UPDATE pnr_status SET
                train_name = %s,
                from_station = %s,
                to_station = %s,
                class_type = %s,
                quota = %s,
                boarding_point = %s,
                available_seats = %s,
                doj = %s,
                last_updated = %s
                WHERE pnr = %s
            """, (
                data['train_name'],
                data['from_station'],
                data['to_station'],
                data['class_type'],
                data['quota'],
                data['boarding_point'],
                data['available_seats'],
                data['doj'],
                datetime.datetime.now(),
                data['pnr']
            ))
            
            # Delete existing passengers for this PNR and insert new ones
            cursor.execute("DELETE FROM pnr_passengers WHERE pnr = %s", (data['pnr'],))
        else:
            # Insert new PNR record
            cursor.execute("""
                INSERT INTO pnr_status (
                    pnr, train_name, from_station, to_station,
                    class_type, quota, boarding_point, available_seats,
                    doj, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['pnr'],
                data['train_name'],
                data['from_station'],
                data['to_station'],
                data['class_type'],
                data['quota'],
                data['boarding_point'],
                data['available_seats'],
                data['doj'],
                datetime.datetime.now()
            ))
        
        # Insert passengers
        for i, passenger in enumerate(data['passengers'], 1):
            cursor.execute("""
                INSERT INTO pnr_passengers (
                    pnr, passenger_number, name, age, gender, 
                    booking_status, current_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['pnr'],
                i,
                passenger['name'],
                passenger['age'],
                passenger['gender'],
                passenger['booking_status'],
                passenger['current_status']
            ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"PNR {data['pnr']} successfully updated/created")
        return jsonify({
            'status': 'success',
            'message': 'PNR data updated successfully',
            'pnr': data['pnr']
        }), 201
        
    except Exception as e:
        logger.error(f"Error updating PNR: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Failed to update PNR: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for service discovery and monitoring"""
    try:
        # Test database connection
        connection = get_db_connection()  # Using the new function
        connection.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return jsonify({
        "status": "healthy", 
        "service": "pnr-status-service",
        "version": "1.0.0",
        "endpoints": [
            "/api/status/<pnr>",
            "/api/update_pnr",
            "/api/health"
        ],
        "dependencies": {
            "database": db_status
        }
    })

if __name__ == '__main__':
    logger.info("Starting PNR Status Service on port 5003")
    app.run(debug=True, host='0.0.0.0', port=5003)