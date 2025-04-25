from flask import Flask, request, jsonify, render_template
import mysql.connector
from config import db_config
import random, datetime
import logging
import requests
import os

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='[BOOKING SERVICE] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service configuration
SEAT_SERVICE_URL = os.environ.get('SEAT_SERVICE_URL', 'http://host.docker.internal:5001')
PNR_SERVICE_URL = os.environ.get('PNR_SERVICE_URL', 'http://host.docker.internal:5003') 
PNR_STATUS_URL = "http://host.docker.internal:5003" # Updated to port 5003
SERVICE_API_KEY = os.environ.get('SERVICE_API_KEY', 'booking-service-key')

def generate_pnr():
    return str(random.randint(1000000000, 9999999999))

def generate_txn_id():
    return str(random.randint(200000000000000, 299999999999999))



from flask import Flask, request, jsonify, render_template, redirect

@app.route('/check-pnr', methods=['POST'])
def check_pnr():
    try:
        pnr = request.form.get('pnr')
        logger.info(f"Checking PNR status for {pnr}")
        
        # Make request to PNR service
        response = requests.get(
            f"{PNR_SERVICE_URL}/api/status/{pnr}",
            headers={"X-API-Key": SERVICE_API_KEY}
        )
        
        if response.status_code == 200:
            # Get the PNR data
            pnr_data = response.json()
            logger.info(f"PNR data retrieved: {pnr_data}")
            
            # Extract the first passenger for backward compatibility
            first_passenger = pnr_data['passengers'][0] if pnr_data['passengers'] else {
                "name": "N/A", "age": "N/A", "gender": "N/A", 
                "booking_status": "N/A", "current_status": "N/A"
            }
            
            # Render the result template with unpacked variables
            return render_template('result.html',
                        pnr=pnr_data['pnr'],
                        name=first_passenger.get('name', 'N/A'),
                        age=first_passenger.get('age', 'N/A'),
                        gender=first_passenger.get('gender', 'N/A'),
                        train_name=pnr_data['train_name'],
                        from_station=pnr_data['from_station'],
                        to_station=pnr_data['to_station'],
                        class_type=pnr_data['class_type'],
                        quota=pnr_data['quota'],
                        boarding_point=pnr_data['boarding_point'],
                        available_seats=pnr_data['available_seats'],
                        doj=pnr_data['doj'],
                        booking_status=first_passenger.get('booking_status', 'N/A'),
                        current_status=first_passenger.get('current_status', 'N/A'),
                        passengers=pnr_data['passengers'])  # Pass all passengers for multi-passenger display
        else:
            # Handle error
            error_message = f"PNR service returned status code {response.status_code}"
            logger.error(error_message)
            return render_template('result.html', 
                                 pnr="Error", 
                                 train_name="Error", 
                                 error=error_message)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to PNR status service: {str(e)}")
        return render_template('result.html', 
                             pnr="Error", 
                             train_name="Error", 
                             error=f"Could not connect to PNR status service: {str(e)}")

@app.route('/book', methods=['POST'])
def book_ticket():
    try:
        data = request.get_json()
        logger.info(f"INCOMING REQUEST: Booking ticket for train {data['train']['number']}")
        
        # First, verify seat availability and reserve seat with Seat Service
        train_number = data['train']['number']
        train_class = data['train']['class']
        
        # For testing - Skip seat service call if not available
        try:
            # Call seat availability service to reserve seat
            reserve_response = requests.post(
                f"{SEAT_SERVICE_URL}/api/reserve/{train_number}/{train_class}",
                headers={"X-API-Key": SERVICE_API_KEY},
                json={"passengers": len(data['passengers'])}
            )
            
            if reserve_response.status_code != 200:
                logger.error(f"Failed to reserve seat: {reserve_response.text}")
                # For testing, we'll continue anyway
                reservation = {"new_availability": f"Seats: {len(data['passengers'])} (simulated)"}
            else:
                # Seat reserved successfully
                reservation = reserve_response.json()
                logger.info(f"Seat reserved successfully: {reservation}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to seat service: {str(e)}")
            # For testing, we'll continue anyway
            reservation = {"new_availability": f"Seats: {len(data['passengers'])} (simulated)"}

        # ✅ Set default values
        pnr = generate_pnr()
        txn_id = generate_txn_id()
        booking_date = datetime.date.today()
        journey_date = datetime.date.today()  # 👈 Automatically set to today's date

        # 🔌 Connect to DB
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # ✅ Insert into bookings table
        cursor.execute("""
            INSERT INTO bookings (
                pnr, transaction_id, train_number, train_name,
                from_station, to_station, journey_date, booking_date,
                quota, boarding_point, class, reservation_upto
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            pnr,
            txn_id,
            data['train']['number'],
            data['train']['name'],
            data['train']['from'],
            data['train']['to'],
            journey_date,
            booking_date,
            data['train']['quota'],
            data['train']['boarding_point'],
            data['train']['class'],
            data['train']['to']
        ))

        booking_id = cursor.lastrowid
        
        # List to store passenger details
        passenger_details = []

        # ✅ Insert passengers
        for passenger in data['passengers']:
            cursor.execute("""
                INSERT INTO passengers (
                    booking_id, name, age, gender, booking_status, current_status
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                booking_id,
                passenger['name'],
                passenger['age'],
                passenger['gender'],
                passenger['seat'],
                "CNF"
            ))
            
            passenger_details.append({
                "name": passenger['name'],
                "age": passenger['age'],
                "gender": passenger['gender'],
                "booking_status": passenger['seat'],
                "current_status": "CNF"
            })

        connection.commit()
        cursor.close()
        connection.close()
        
        # Notify PNR Status Service about the new booking
        try:
            # Prepare the booking data for PNR Status Service
            pnr_data = {
                "pnr": pnr,
                "train_name": data['train']['name'],
                "from_station": data['train']['from'],
                "to_station": data['train']['to'],
                "class_type": data['train']['class'],
                "quota": data['train']['quota'],
                "boarding_point": data['train']['boarding_point'],
                "available_seats": reservation.get('new_availability', 'Unknown'),
                "doj": journey_date.strftime('%Y-%m-%d'),
                "passengers": passenger_details
            }
            
            logger.info(f"Sending PNR data to PNR service: {pnr_data}")
            
            # Send booking data to PNR Status Service
            pnr_response = requests.post(
                f"{PNR_SERVICE_URL}/api/update_pnr",
                headers={"X-API-Key": SERVICE_API_KEY},
                json=pnr_data,
                timeout=5  # Add timeout to prevent hanging
            )
            
            logger.info(f"PNR Service response: {pnr_response.status_code} - {pnr_response.text}")
            
            if pnr_response.status_code != 201:
                logger.warning(f"PNR Status Service notification failed: {pnr_response.text}")
                # Continue even if PNR service notification fails - we can sync later
            else:
                logger.info(f"PNR Status Service notified successfully")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to PNR Status Service: {str(e)}")
            # We'll continue even if we can't notify the PNR service
        
        logger.info(f"Booking successful - PNR: {pnr}")

        return jsonify({
            "status": "success",
            "pnr": pnr,
            "transaction_id": txn_id,
            "message": "Ticket booked successfully",
            "seat_info": reservation.get('new_availability', 'Confirmed')
        }), 201

    except Exception as e:
        logger.error(f"Error booking ticket: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 🏠 Home page - Booking form
@app.route('/')
def show_form():
    train_data = {
        'number': request.args.get('number'),
        'name': request.args.get('name'),
        'from': request.args.get('from'),
        'to': request.args.get('to'),
        'journey_date': request.args.get('date'),
        'quota': request.args.get('quota', 'General'),
        'class': request.args.get('class'),
        'boarding_point': request.args.get('boarding'),
        'seat': request.args.get('seat')
    }
    
    # Log incoming requests from seat service
    if train_data['number']:
        logger.info(f"INCOMING REQUEST from Seat Service: Booking form accessed for Train #{train_data['number']}")
    
    # If we have a train number but missing other details, fetch from seat service
    if train_data['number'] and (not train_data['name'] or not train_data['from']):
        try:
            # Get more train details if needed
            logger.info(f"Fetching train details from seat service for #{train_data['number']}")
            response = requests.get(
                f"{SEAT_SERVICE_URL}/api/train/{train_data['number']}",
                headers={"X-API-Key": SERVICE_API_KEY}
            )
            
            if response.status_code == 200:
                train_info = response.json()
                logger.info(f"Retrieved train info: {train_info}")
                # Update any missing information
                # (In a real implementation, this would populate from the train info)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get train details: {str(e)}")
    
    return render_template('book_form.html', train=train_data)

@app.route('/api/check_pnr/<pnr>', methods=['GET'])
def check_pnr_status(pnr):
    """API endpoint to check PNR status by forwarding to PNR service"""
    try:
        logger.info(f"Checking PNR status for {pnr}")
        response = requests.get(
            f"{PNR_SERVICE_URL}/api/status/{pnr}",
            headers={"X-API-Key": SERVICE_API_KEY}
        )
        
        logger.info(f"PNR Service response: {response.status_code}")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to PNR status service: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Could not connect to PNR status service"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for service discovery and monitoring"""
    pnr_health = check_pnr_service_health()
    logger.info(f"PNR Service health: {pnr_health}")
    
    return jsonify({
        "status": "healthy", 
        "service": "booking-service",
        "version": "1.0.0",
        "endpoints": [
            "/book",
            "/api/check_pnr/<pnr>",
            "/api/health"
        ],
        "dependencies": {
            "seat-service": check_seat_service_health(),
            "pnr-service": pnr_health
        }
    })

def check_seat_service_health():
    """Check if seat service is healthy"""
    try:
        response = requests.get(f"{SEAT_SERVICE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            return "healthy"
        return "unhealthy"
    except:
        return "unreachable"

def check_pnr_service_health():
    """Check if PNR service is healthy"""
    try:
        response = requests.get(f"{PNR_SERVICE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            return "healthy"
        return "unhealthy"
    except Exception as e:
        logger.error(f"PNR health check error: {str(e)}")
        return "unreachable"

if __name__ == '__main__':
    logger.info("Starting Booking Service on port 5002")
    app.run(debug=True, host='0.0.0.0', port=5002)