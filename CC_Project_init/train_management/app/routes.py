import logging
from flask import Blueprint, render_template, request, jsonify
import requests
from db import get_db_connection

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='[TRAIN SEARCH] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# --- Service URLs (use your actual host IP if needed) ---
SEAT_AVAILABILITY_URL = "http://host.docker.internal:5001/check_seat"
HOTEL_RECOMMENDER_URL = "http://host.docker.internal:3005/api/recommend"


@bp.route('/', methods=['GET', 'POST'])
def index():
    logger.info("Homepage accessed")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT source, destination FROM trains")
    source_dest_pairs = cursor.fetchall()

    places_dict = {}
    for source, destination in source_dest_pairs:
        if source in places_dict:
            if destination not in places_dict[source]:
                places_dict[source].append(destination)
        else:
            places_dict[source] = [destination]

    for source in places_dict:
        places_dict[source] = sorted(places_dict[source])
    places_dict = dict(sorted(places_dict.items()))

    results = []
    hotels = []

    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        budget_input = request.form.get('budget', '200')  # Default to ₹200

        logger.info(f"Train search request: Source={source}, Destination={destination}")

        if source.lower() != destination.lower():
            # --- Get matching trains ---
            query = """
                SELECT DISTINCT train_number, train_name, station_name, departure, source, destination
                FROM trains
                WHERE LOWER(source) = %s AND LOWER(destination) = %s
            """
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (source.lower(), destination.lower()))
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} trains for route {source} to {destination}")

            # --- Clean and normalize destination name ---
            dest = destination.replace(' Flag Stn', '').replace(' Junction', '')

            # --- Normalize budget ---
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

            # --- Fetch hotel recommendations ---
            try:
                logger.info(f"Fetching hotel recommendations for {dest} with budget {budget}")
                hotel_response = requests.get(HOTEL_RECOMMENDER_URL, params={
                    'location': dest,
                    'budget': budget
                })
                hotels = hotel_response.json()
                logger.info(f"Hotel recommendations received: {hotels}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching hotels: {str(e)}")
                hotels = []

    cursor.close()
    conn.close()

    return render_template('index.html', places_dict=places_dict, results=results, hotels=hotels)


@bp.route('/api/check_seat', methods=['POST'])
def api_check_seat():
    """Proxy endpoint for seat availability service"""
    data = request.json
    logger.info(f"OUTGOING REQUEST to Seat Service: Checking seats for train #{data.get('train_number')}")

    try:
        response = requests.post(SEAT_AVAILABILITY_URL, json=data)
        response_data = response.json()
        logger.info(f"INCOMING RESPONSE from Seat Service: Status={response.status_code}, Data={response_data}")
        return jsonify(response_data), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Communication Error with Seat Service: {str(e)}")
        return jsonify({"error": f"Error fetching seat availability: {str(e)}"}), 500


@bp.route('/api/check_seat_and_recommend', methods=['POST'])
def api_check_seat_and_recommend():
    data = request.json
    logger.info(f"Processing request for train #{data.get('train_number')}: Destination={data.get('destination')}")

    try:
        # --- Check seat availability ---
        seat_response = requests.post(SEAT_AVAILABILITY_URL, json=data)
        seat_data = seat_response.json()
        logger.info(f"Seat availability response: {seat_data}")

        # --- Normalize destination and budget ---
        dest = data.get('destination', '').replace(' Flag Stn', '').replace(' Junction', '')
        budget_value = data.get('budget', 200)

        try:
            budget_value = float(budget_value)
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

        # --- Get hotel recommendations ---
        dest_hotels = requests.get(HOTEL_RECOMMENDER_URL, params={
            'location': dest,
            'budget': budget
        }).json()
        logger.info(f"Hotel recommendations - Destination: {dest_hotels}")

        combined_response = {
            'seat_info': seat_data.get('seat_info', {}),
            'hotels_at_destination': dest_hotels
        }
        return jsonify(combined_response), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with services: {str(e)}")
        return jsonify({"error": f"Service communication failed: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
