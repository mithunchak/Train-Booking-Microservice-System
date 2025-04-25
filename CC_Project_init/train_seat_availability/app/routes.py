from waitress import serve
from flask import Flask, render_template, request, jsonify, redirect, url_for
import random
import logging
import requests
import os
from db import get_db
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='[SEAT SERVICE] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Service configuration
BOOKING_SERVICE_URL = os.environ.get('BOOKING_SERVICE_URL', 'http://host.docker.internal:5002')
SERVICE_API_KEY = os.environ.get('SERVICE_API_KEY', 'seat-service-key')

@app.route("/")
def home():
    # Get URL parameters
    train_number = request.args.get('train_number')
    train_name = request.args.get('train_name')
    source = request.args.get('source')
    destination = request.args.get('destination')
    
    if train_number:
        logger.info(f"INCOMING REQUEST from Train Search Service: Homepage accessed with parameters - Train #{train_number}, {train_name}, {source} to {destination}")
    else:
        logger.info("Homepage accessed without parameters")
    
    # The template will handle the URL parameters
    return render_template("index.html")

@app.route("/api/train/<train_number>", methods=["GET"])
def get_train_availability(train_number):
    """API endpoint to get seat availability by train number only"""
    logger.info(f"API REQUEST: Get seat availability for Train #{train_number}")
    
    # Verify service authentication if needed
    api_key = request.headers.get('X-API-Key')
    if api_key not in ['train-search-key', 'booking-service-key', SERVICE_API_KEY]:
        logger.warning(f"Unauthorized API request for train #{train_number}")
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    cur = db.cursor()
    
    # Check if seat availability already exists for this train
    cur.execute("""
        SELECT train_class, availability FROM seat_availability
        WHERE train_number = %s
    """, (train_number,))
    
    rows = cur.fetchall()
    
    seat_availability = {}
    
    if rows:
        # Return existing seat availability
        for row in rows:
            train_class, availability = row
            seat_availability[train_class] = availability
        logger.info(f"Retrieved from database: Seat availability for Train #{train_number}")
    else:
        # Generate and insert random availability
        logger.info(f"No existing data. Train #{train_number} not found in database")
        return jsonify({"error": "Train not found"}), 404
    
    cur.close()
    
    response_data = {
        "train_number": train_number,
        "seat_info": seat_availability
    }
    
    logger.info(f"OUTGOING RESPONSE: Sending seat information for Train #{train_number}")
    
    return jsonify(response_data)

@app.route("/check_seat", methods=["POST"])
def check_seat():
    data = request.get_json()
    train_number = data.get("train_number")
    
    # Additional data can be received but is not required
    train_name = data.get("train_name")
    source = data.get("source")
    destination = data.get("destination")
    
    logger.info(f"INCOMING REQUEST: Check seat availability for Train #{train_number}")
    
    # Log the origin of the request
    remote_addr = request.remote_addr
    logger.info(f"Request received from: {remote_addr}")
    
    if not train_number:
        logger.warning("Missing train number in request")
        return jsonify({"message": "Train number parameter is required"}), 400
    
    db = get_db()
    cur = db.cursor()
    
    # Check if seat availability already exists for this train
    cur.execute("""
        SELECT train_class, availability FROM seat_availability
        WHERE train_number = %s
    """, (train_number,))
    
    rows = cur.fetchall()
    
    seat_availability = {}
    
    if rows:
        # Return existing seat availability
        for row in rows:
            train_class, availability = row
            seat_availability[train_class] = availability
        logger.info(f"Retrieved from database: Seat availability for Train #{train_number}")
    else:
        # Generate and insert random availability
        logger.info(f"Generating new seat availability for Train #{train_number}")
        train_classes = ["Sleeper", "AC", "Non-AC"]
        for train_class in train_classes:
            # Generate random seat availability based on schema
            status_type = random.choice(["Available", "Waiting List", "No Seats"])
            
            if status_type == "Available":
                available_seats = random.randint(1, 50)
                availability = f"{available_seats} Available"
            elif status_type == "Waiting List":
                waiting_list = random.randint(1, 20)
                availability = f"Waiting List ({waiting_list} people)"
            else:
                availability = "No Seats Available"
            
            seat_availability[train_class] = availability
            
            # Insert into DB - ensuring the data fits the schema
            cur.execute("""
                INSERT INTO seat_availability (train_number, train_class, availability)
                VALUES (%s, %s, %s)
            """, (train_number[:10], train_class[:20], availability[:50]))
        
        db.commit()
        logger.info(f"New seat availability for Train #{train_number} saved to database")
    
    cur.close()
    
    response_data = {
        "train_number": train_number,
        "train_name": train_name,
        "source": source,
        "destination": destination,
        "seat_info": seat_availability
    }
    
    logger.info(f"OUTGOING RESPONSE: Sending seat information for Train #{train_number}")
    logger.info(f"Response data: {response_data}")
    
    return jsonify(response_data)

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for service discovery and monitoring"""
    return jsonify({
        "status": "healthy", 
        "service": "seat-availability",
        "version": "1.0.0",
        "endpoints": [
            "/api/train/<train_number>",
            "/check_seat",
            "/api/health"
        ]
    })

@app.route("/api/reserve/<train_number>/<train_class>", methods=["POST"])
def reserve_seat(train_number, train_class):
    """API endpoint to temporarily reserve a seat in a train"""
    logger.info(f"INCOMING REQUEST: Reserve seat in Train #{train_number}, Class: {train_class}")
    
    # Verify service authentication
    api_key = request.headers.get('X-API-Key')
    if api_key != 'booking-service-key':
        logger.warning(f"Unauthorized reservation request for Train #{train_number}")
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    reservation_id = random.randint(100000, 999999)
    
    db = get_db()
    cur = db.cursor()
    
    # Check current availability
    cur.execute("""
        SELECT availability FROM seat_availability
        WHERE train_number = %s AND train_class = %s
    """, (train_number, train_class))
    
    row = cur.fetchone()
    
    if not row:
        return jsonify({"error": "Train or class not found"}), 404
    
    availability = row[0]
    
    # If seats are available, decrement by 1
    if "Available" in availability:
        try:
            seats = int(availability.split(" ")[0])
            if seats > 0:
                new_availability = f"{seats - 1} Available"
                
                # Update availability
                cur.execute("""
                    UPDATE seat_availability 
                    SET availability = %s
                    WHERE train_number = %s AND train_class = %s
                """, (new_availability, train_number, train_class))
                
                db.commit()
                logger.info(f"Seat reserved in Train #{train_number}, Class: {train_class}")
                
                return jsonify({
                    "status": "success",
                    "reservation_id": reservation_id,
                    "train_number": train_number,
                    "class": train_class,
                    "new_availability": new_availability
                })
            else:
                return jsonify({"error": "No seats available"}), 400
        except Exception as e:
            logger.error(f"Error processing reservation: {str(e)}")
            return jsonify({"error": "Failed to process reservation"}), 500
    else:
        return jsonify({"error": "No seats available for reservation"}), 400

if __name__ == "__main__":
    logger.info("Starting Seat Availability Service on port 5001")
    serve(app, host='127.0.0.1', port=5001)