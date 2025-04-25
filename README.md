# Train-Booking-Microservice-System
Train Booking System - Technical Report
							M Mithun Kumar       
Executive Summary
This report provides a comprehensive analysis of the Train Booking System, a microservices-based application designed to facilitate train searching, seat availability checking, ticket booking, PNR status verification, and hotel recommendations. The system employs a modern microservices architecture with four distinct services, each with its own database and functionalities, communicating via RESTful APIs.
1. System Architecture Overview
The Train Booking System follows a distributed microservices architecture pattern where each service operates independently yet cooperates to deliver a cohesive user experience. This approach provides several advantages:
Scalability: Each service can be scaled independently based on demand
Resilience: Failure in one service doesn't necessarily affect others
Technology flexibility: Services can use different technologies as needed
Team organization: Development teams can focus on specific services
1.1 Service Communication Flow
The system follows this general flow of operations:
Users search for trains between source and destination (Train Management Service)
System checks seat availability for selected trains (Seat Availability Service)
Users book tickets with passenger details (Booking Service)
System generates PNR numbers for tracking (Booking Service)
Users can check PNR status for their bookings (PNR Status Service)
System recommends hotels at the destination city (Hotel Recommendation Integration)

1.2Component Diagram
![Screenshot 2025-04-25 203734](https://github.com/user-attachments/assets/b0ab83a5-6cbf-4b73-8c94-18272bd5ac10)

2. Service Details
2.1 Train Management Service (Port 5000)
2.1.1 Core Functionality
Provides train search capabilities between source and destination
Displays train details including train numbers, names, and schedules
Offers hotel recommendations at destination cities
Acts as a gateway to seat availability service
2.1.2 Technical Implementation
Flask Blueprint architecture for route organization
Database queries for train search using source and destination parameters
Integration with external hotel recommendation service
Proxy endpoints for seat availability service
2.1.3 Key Code Analysis
The service uses a Blueprint-based structure for route organization:
bp = Blueprint('main', __name__)

The main search functionality queries the database for trains matching source and destination:
query = """
    SELECT DISTINCT train_number, train_name, station_name, departure, source, destination
    FROM trains
    WHERE LOWER(source) = %s AND LOWER(destination) = %s
"""

The service also implements a proxy endpoint for seat availability:
@bp.route('/api/check_seat', methods=['POST'])
def api_check_seat():
    """Proxy endpoint for seat availability service"""
    # Implementation details
    
Frontend:
![Screenshot 2025-04-25 204607](https://github.com/user-attachments/assets/6c3559c1-f21e-452c-8556-53e16cbdd13a)

Backend:
![Screenshot 2025-04-25 204658](https://github.com/user-attachments/assets/032b3a35-e557-47a6-a788-7545abc9555e)

2.2 Seat Availability Service (Port 5001)
2.2.1 Core Functionality
Checks real-time seat availability for specific trains
Provides information on available seats by class type
Supports seat reservations for the booking process
Manages seat inventory through database persistence
2.2.2 Technical Implementation
Flask application with direct database interactions
Random seat availability generation for demonstration
API key authentication for service-to-service communication
Health check endpoint for monitoring
2.2.3 Key Code Analysis
The service generates and persists seat availability data:
# Generate and insert random availability
train_classes = ["Sleeper", "AC", "Non-AC"]
for train_class in train_classes:
    # Generate random seat availability based on schema
    status_type = random.choice(["Available", "Waiting List", "No Seats"])
    
    if status_type == "Available":
        available_seats = random.randint(1, 50)
        availability = f"{available_seats} Available"
    # Additional logic

The service implements secure API authentication:
# Verify service authentication if needed
api_key = request.headers.get('X-API-Key')
if api_key not in ['train-search-key', 'booking-service-key', SERVICE_API_KEY]:
    logger.warning(f"Unauthorized API request for train #{train_number}")
    return jsonify({"error": "Unauthorized"}), 401
    
Frontend:
![Screenshot 2025-04-25 204728](https://github.com/user-attachments/assets/3e700baa-c669-4117-a99a-119337e51d61)

Backend:
![Screenshot 2025-04-25 204921](https://github.com/user-attachments/assets/10fef23e-b177-4fbd-a385-68765a5a9a2d)

2.3 Booking Service (Port 5002)
2.3.1 Core Functionality
Provides a booking form for train ticket reservations
Processes passenger information and creates bookings
Generates PNR numbers for tracking reservations
Integrates with seat availability and PNR status services
2.3.2 Technical Implementation
Flask application with form handling and API endpoints
Database transactions for booking creation
Inter-service communication with seat and PNR services
Transaction ID generation for payment tracking
2.3.3 Key Code Analysis
The booking process involves multiple steps:
Reserve seats through the seat service:
reserve_response = requests.post(
    f"{SEAT_SERVICE_URL}/api/reserve/{train_number}/{train_class}",
    headers={"X-API-Key": SERVICE_API_KEY},
    json={"passengers": len(data['passengers'])}
)

Create booking records in the database:
cursor.execute("""
    INSERT INTO bookings (
        pnr, transaction_id, train_number, train_name,
        from_station, to_station, journey_date, booking_date,
        quota, boarding_point, class, reservation_upto
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    # Parameter values
))

Notify the PNR service:
pnr_response = requests.post(
    f"{PNR_SERVICE_URL}/api/update_pnr",
    headers={"X-API-Key": SERVICE_API_KEY},
    json=pnr_data,
    timeout=5
)

Frontend:
![Screenshot 2025-04-25 205028](https://github.com/user-attachments/assets/b7e71e08-75c7-4a33-b0ca-5aeae0f7efe1)

Backend:
![Screenshot 2025-04-25 205115](https://github.com/user-attachments/assets/a70116dc-6184-44a5-b19f-39274534043c)

2.4 PNR Status Service (Port 5003)
2.4.1 Core Functionality
Provides PNR status checking capabilities
Stores and manages PNR records and their current status
Displays passenger details and journey information
Offers both UI and API interfaces for PNR verification
2.4.2 Technical Implementation
Flask application with form and API endpoints
Database structure for PNR and passenger information
Dynamic table creation for first-time setup
Service health monitoring endpoints
2.4.3 Key Code Analysis
The service creates necessary database tables if they don't exist:
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
The service supports multiple passengers per PNR:
# Insert passengers
for i, passenger in enumerate(data['passengers'], 1):
    cursor.execute("""
        INSERT INTO pnr_passengers (
            pnr, passenger_number, name, age, gender, 
            booking_status, current_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        # Parameter values
    ))
    
Frontend:
![Screenshot 2025-04-25 205158](https://github.com/user-attachments/assets/d3fee861-b973-4dfc-97eb-6bcec1e0a891)

Backend:
![Screenshot 2025-04-25 205251](https://github.com/user-attachments/assets/1c6f9a80-4788-498b-9e71-3855de9a3551)

2.5 Hotel Recommendation Integration
2.5.1 Core Functionality
Suggests hotels at the destination city when users search for trains
Categorizes hotels based on budget preferences
Enhances the travel planning experience with accommodation options
Provides hotel details including name, price, and ratings
2.5.2 Technical Implementation
Integration with external Hotel Recommendation Service via REST API
Budget classification algorithm for personalized recommendations
Destination name normalization for improved matching
Combined endpoint for seat availability and hotel recommendations
2.5.3 Key Code Analysis
The service connects to an external hotel recommendation service:
HOTEL_RECOMMENDER_URL = "http://host.docker.internal:3005/api/recommend"

Budget classification algorithm:
try:
    budget_value = float(budget_input)
    if budget_value <= 0:
        budget = 'medium'
    elif budget_value <= 100:
        budget = 'low'
    elif budget_value <= 250:
        budget = 'medium'
    else:
        budget = 'high'
except (ValueError, TypeError):
    budget = 'medium'

Destination name normalization:
dest = destination.replace(' Flag Stn', '').replace(' Junction', '')

API integration for hotel recommendations:
try:
    hotel_response = requests.get(HOTEL_RECOMMENDER_URL, params={
        'location': dest,
        'budget': budget
    })
    hotels = hotel_response.json()
    logger.info(f"Hotel recommendations received: {hotels}")
except requests.exceptions.RequestException as e:
    logger.error(f"Error fetching hotels: {str(e)}")
    hotels = []

Combined endpoint for seat availability and hotel recommendations:
@bp.route('/api/check_seat_and_recommend', methods=['POST'])
def api_check_seat_and_recommend():
    # Implementation details
    combined_response = {
        'seat_info': seat_data.get('seat_info', {}),
        'hotels_at_destination': dest_hotels
    }
    return jsonify(combined_response), 200

Hotel data structure from API response:
{
  "hotels_at_destination": [
    {
      "_v": 0,
      "id": "680b628f2617c0340f497598",
      "hotelName": "Majestic Chic Lodge",
      "location": "Tirupati",
      "pricePerNight": 156,
      "rating": 4
    }
  ]
}

Logs:

![Screenshot 2025-04-25 205345](https://github.com/user-attachments/assets/7be3fbbc-2991-46d1-8bf9-eab76b326bf8)

3. DevOps Implementation
3.1 Containerization Strategy
The system utilizes Docker for containerization with a multi-container setup defined in docker-compose.yml:
Each service has its own container
Each database has a dedicated container
Volumes for database persistence
Health checks to ensure dependencies are ready
Environment variable configuration
3.2 Docker Compose Configuration
Key aspects of the Docker Compose configuration:
Service dependency management:
depends_on:
  train-db:
    condition: service_healthy

Volume management for data persistence:
volumes:
  - train-db-data:/var/lib/mysql

Environment variable configuration:
environment:
  - DB_HOST=train-db
  - DB_USER=root
  - DB_PASSWORD=root_password
  - DB_NAME=train_db

Health checks for service readiness:
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root","-p101010"]
  interval: 5s
  timeout: 5s
  retries: 10
  
Docker containers:

![Screenshot 2025-04-25 205438](https://github.com/user-attachments/assets/8b1f0854-2be2-441f-b763-5ece8621fd38)

4. Database Design
4.1 Multiple Database Approach
Each service maintains its own database:
train_db - Used by Train Management Service
Tables: trains, stations, routes
train_seat_availability - Used by Seat Availability Service
Tables: seat_availability
booking_services - Used by Booking Service
Tables: bookings, passengers
pnr_db - Used by PNR Status Service
Tables: pnr_status, pnr_passengers
4.2 Schema Organization
The database schemas follow service-specific requirements:
Train Management: Stores train routes, schedules, and station information
Seat Availability: Maintains seat availability data by train and class
Booking: Records booking information including passengers and transactions
PNR Status: Tracks PNR records and their current status
5. API Design and Cross-Service Communication
5.1 API Patterns
The system implements RESTful APIs with these patterns:
Resource-based URLs: e.g., /api/train/<train_number>
HTTP methods: GET for retrieval, POST for creation/updates
JSON responses: All APIs return structured JSON data
Status codes: Proper HTTP status codes (200, 201, 400, 401, 404, 500)
5.2  API End-points:
Train Search Service (Blueprint)
Endpoints:
/ (GET/POST): Homepage for train search
/api/check_seat (POST): API endpoint to proxy requests to Seat Service
/api/check_seat_and_recommend (POST): Combined endpoint that checks seat availability and recommends hotels
The Train Search service allows users to search for trains between source and destination stations, and integrates with the Seat Availability service.
Seat Availability Service (port 5001)
Endpoints:
/ (GET): Homepage
/api/train/<train_number> (GET): API endpoint to get seat availability for a specific train
/check_seat (POST): Endpoint to check seat availability
/api/health (GET): Health check endpoint
/api/reserve/<train_number>/<train_class> (POST): API to reserve a seat
The Seat service manages seat availability information for trains.
Hotel Recommender Service (port 3005)
Endpoints:
/api/hotels (POST): Create a new hotel entry
/api/recommend (GET): Get hotel recommendations based on location and budget
The Hotel Recommender service provides hotel recommendations based on the destination and budget.
Booking Service (port 5002)
Endpoints:
/ (GET): Home page showing booking form
/book (POST): Endpoint to book a ticket
/check-pnr (POST): Form submission to check PNR status
/api/check_pnr/<pnr> (GET): API endpoint to check PNR status
/api/health (GET): Health check endpoint for service monitoring
The booking service is responsible for creating new ticket bookings. It communicates with:
Seat Service to check/reserve seats
PNR Service to update/create PNR records
PNR Service (port 5003)
Endpoints:
/ (GET): Home page with form to check PNR status
/submit (POST): Form submission endpoint for PNR status checking
/api/status/<pnr> (GET): API endpoint to get PNR status
/api/update_pnr (POST): API endpoint for creating/updating PNR records
/api/health (GET): Health check endpoint
The PNR service maintains PNR (Passenger Name Record) information, which tracks ticket bookings and passenger details.
Service Connections
Train Search → Seat Service: To check seat availability when searching for trains
Train Search → Hotel Service: To get hotel recommendations at the destination
Booking Service → Seat Service: To reserve seats during booking
Booking Service → PNR Service: To create/update PNR records after booking
User → PNR Service: To check PNR status directly

5.2 Authentication
Services implement API key authentication for secure inter-service communication:
api_key = request.headers.get('X-API-Key')
if not validate_api_key(request):
    logger.warning(f"Unauthorized API access attempt")
    return jsonify({'error': 'Unauthorized access'}), 401

5.3 Error Handling
Consistent error handling across services with logging:
except Exception as e:
    logger.error(f"Error in get_pnr_status: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({'error': f'Error processing request: {str(e)}'}), 500

6. Logging Strategy
The system implements a comprehensive logging strategy:
Service identification: Each log entry includes the service name
[TRAIN SEARCH] 2023-04-25 12:34:56 - INFO - Homepage accessed

Request tracking: Logs incoming and outgoing requests
logger.info(f"INCOMING REQUEST: Check seat availability for Train #{train_number}")

Response logging: Logs response data for debugging
logger.info(f"OUTGOING RESPONSE: Sending seat information for Train #{train_number}")

Error logging: Detailed error logging with stack traces
logger.error(f"Error processing request: {str(e)}")
logger.error(traceback.format_exc())

7. System Enhancement Opportunities
7.1 Security Improvements
Implement OAuth 2.0 for more robust authentication
Add rate limiting to prevent API abuse
Introduce HTTPS for all service communications
Encrypt sensitive data in database storage
7.2 Performance Optimization
Implement caching for frequently accessed data
Optimize database queries with proper indexing
Add connection pooling for database connections
Implement asynchronous processing for non-critical operations
7.3 Feature Enhancements
Payment gateway integration
User authentication and accounts
Email/SMS notifications for booking updates
Mobile app integration via APIs
Analytics dashboard for system usage
8. Conclusion
The Train Booking System with integrated hotel recommendations demonstrates effective use of microservices architecture for a complex domain. Its modular design allows for independent scaling, development, and maintenance of each component while ensuring a cohesive user experience through well-defined API interfaces. The containerized deployment strategy enables consistent development and production environments, while the service-specific databases maintain proper domain boundaries.
The addition of hotel recommendations enhances the overall user experience by providing end-to-end travel planning capabilities within a single system. This integration demonstrates how the architecture can be extended to incorporate additional services while maintaining the independence and resilience of the core booking functionality.
The system successfully implements the core functionality required for train ticket booking and travel planning while providing a foundation for future enhancements and scalability.

