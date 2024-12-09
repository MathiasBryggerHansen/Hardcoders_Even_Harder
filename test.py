def validate_request_format(request_data):
    required_fields = {
        'email': (str, None),
        'age': (int, 0),
        'subscription_tier': (str, ''),
        'user_data': (dict, {})
    }

    error_msg = ""

    # Check if all required fields are present and have correct data types
    for field, (expected_type, expected_default) in required_fields.items():
        if field not in request_data:
            error_msg = f"Missing field: {field}"
            return False, "400 Missing necessary field"

        if not isinstance(request_data[field], expected_type):
            error_msg = f"Incorrect type for field '{field}': got {type(request_data[field]).__name__}, expected {expected_type.__name__}"
            return False, "422 Unprocessable Entity"

        # Handle null values with a default value
        if request_data[field] is None:
            request_data[field] = expected_default

    return True, ""


# Example usage:
request_data_example = {
    'email': 'test@example.com',
    'age': 30,
    'subscription_tier': 'premium',
    'user_data': {'key': 'value'}
}

is_valid, error_msg = validate_request_format(request_data_example)
print(f"Valid: {is_valid}, Error Message: '{error_msg}'")


def validate_user_data(user_data) -> tuple[bool, str]:
    # Debug print to help with debugging
    print("Validating user data:", user_data)

    try:
        # Step 1: Check required fields
        if not isinstance(user_data, dict):
            return (False, "User data should be a dictionary.")

        preferences = user_data.get('preferences')
        payment_info = user_data.get('payment_info')
        usage_metrics = user_data.get('usage_metrics')

        if not all(key in user_data for key in ['preferences', 'payment_info', 'usage_metrics']):
            return (False, "Missing required fields.")

        # Step 2: Validate preferences
        if not isinstance(preferences, dict):
            raise ValueError("Preferences should be a dictionary.")

        notifications = preferences.get('notifications')
        theme = preferences.get('theme')

        if not all(isinstance(notifications, bool) and isinstance(theme, str)):
            raise ValueError("Notifications should be a boolean and theme should be a string.")

        # Step 3: Validate payment_info
        if not isinstance(payment_info, dict):
            raise ValueError("Payment info should be a dictionary.")

        method = payment_info.get('method')
        currency = payment_info.get('currency')

        if method is None or currency is None:
            raise ValueError("Method and currency are required in payment info.")

        # Step 4: Validate usage_metrics
        if not isinstance(usage_metrics, (list, tuple)) or len(usage_metrics) < 3 or len(usage_metrics) > 10:
            raise ValueError("Usage metrics should be an array with between 3 to 10 numbers.")

        if not all(isinstance(x, (int, float)) for x in usage_metrics):
            raise ValueError("All elements in usage metrics should be numbers.")

        # If all checks pass
        return (True, "")

    except IndexError as e:
        print(f"Array index out of bounds: {e}")
        return (False, "Array index out of bounds.")
    except TypeError as e:
        print(f"Type conversion error: {e}")
        return (False, "Type conversion error.")


# Test code

def validate_business_rules(email: str, age: any, subscription_tier: str) -> tuple[bool, str]:
    # Initialize is_valid as False and error_msg as an empty string
    is_valid = False
    error_msg = ""

    try:
        # Validate Email
        if "@validcompany.com" not in email:
            raise ValueError("Email must contain '@validcompany.com'")

        # Validate Age
        age_int = int(age)
        if age_int < 18 or age_int > 100:
            raise ValueError("Age must be between 18 and 100")

        # Validate Subscription Tier
        valid_tiers = ['basic', 'pro', 'enterprise']
        if subscription_tier not in valid_tiers:
            raise ValueError(f"Subscription tier must be one of {valid_tiers}")

        # If all validations pass, set is_valid to True and error_msg to an empty string
        is_valid = True
        error_msg = ""

    except (TypeError, ValueError) as e:
        # Handle type conversion errors and other ValueError exceptions
        is_valid = False
        error_msg = "422"

    return is_valid, error_msg


def calculate_metrics(age, usage_metrics, payment_method, subscription_tier):
    # Initialize default values for output dictionary
    result = {
        'base_price': None,
        'risk_score': None,
        'premium_price': None
    }

    # Validate input types and handle edge cases
    if age is None or not isinstance(age, (int, float)):
        return {'error': 'Invalid age'}
    if usage_metrics is None or not isinstance(usage_metrics, dict):
        return {'error': 'Invalid usage metrics'}
    if payment_method is None or not isinstance(payment_method, str):
        return {'error': 'Invalid payment method'}
    if subscription_tier is None or not isinstance(subscription_tier, str) or subscription_tier.lower() not in ['basic',
                                                                                                                'pro',
                                                                                                                'enterprise']:
        return {'error': 'Invalid subscription tier'}

    # Determine base price based on subscription tier
    try:
        subscription_tier = subscription_tier.lower()
        if subscription_tier == 'basic':
            result['base_price'] = 10
        elif subscription_tier == 'pro':
            result['base_price'] = 25
        elif subscription_tier == 'enterprise':
            result['base_price'] = 50
    except ValueError as e:
        return {'error': str(e)}

    # Calculate risk score
    try:
        avg_usage = usage_metrics.get('avg_usage', 0)
        if avg_usage == 0:
            result['risk_score'] = 500
        else:
            risk_score = age * avg_usage / 10
            result['risk_score'] = round(risk_score, 2)  # Round to two decimal places for consistency
    except ZeroDivisionError as e:
        return {'error': str(e)}

    # Calculate premium price
    try:
        if payment_method.lower() == 'crypto':
            premium_multiplier = 1.5
            result['premium_price'] = round(result['base_price'] * premium_multiplier, 2)
        else:
            result['premium_price'] = result['base_price']
    except ZeroDivisionError as e:  # Catch specific exceptions
        return {'error': 'Integer overflow'}
    except TypeError as e:
        return {'error': 'Type error'}

    # Return the final result dictionary
    return result


# Example usage:
age = 30
usage_metrics = {'avg_usage': 15}
payment_method = 'crypto'
subscription_tier = 'pro'

result = calculate_metrics(age, usage_metrics, payment_method, subscription_tier)
print(result)

# Additional test cases
test_cases = [
    (30, {'avg_usage': 15}, 'crypto', 'pro'),
    (25, None, 'credit_card', 'basic'),  # Invalid usage metrics
    (None, {'avg_usage': 20}, 'paypal', 'pro'),  # Invalid age
    ('abc', {'avg_usage': 30}, 'bank_transfer', 'enterprise'),  # Invalid subscription tier
]

for tc in test_cases:
    result = calculate_metrics(*tc)
    print(result)

from datetime import datetime
from flask import request, jsonify


def check_rate_limit(user_id):
    if user_id in rate_limit_counter:
        current_time = datetime.now().timestamp()
        old_requests = [req for req, timestamp in rate_limit_counter[user_id] if
                        (current_time - timestamp) <= RATE_LIMIT_PERIOD]

        if len(old_requests) >= RATE_LIMIT_THRESHOLD:
            return True

    if user_id not in rate_limit_counter:
        rate_limit_counter[user_id] = []

    rate_limit_counter[user_id].append((request.path, datetime.now().timestamp()))
    return False


# Example data validation function (you should replace this with your actual validation logic)
def validate_data(data):
    required_fields = {'key1', 'key2'}
    if not required_fields.issubset(data.keys()):
        raise ValueError("Missing required fields")

    # Additional schema or business logic validation can go here
    # Example:
    # if data['value'] < 0:
    #     return abort(422, description="Invalid value")


def calculate_metrics(data):
    try:
        # Your calculation logic here
        metrics = {'metric1': data['key1'], 'metric2': data['key2']}
        return metrics
    except Exception as e:
        raise InternalServerError("Error during metric calculation: {}".format(e))


def process_request():
    app.logger.info("Processing request...")

    # Check rate limit
    user_id = request.headers.get('X-User-ID')
    if check_rate_limit(user_id):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    # Get and validate data
    try:
        app.logger.debug("Attempting to get JSON data")
        data = request.json
        validate_data(data)
        app.logger.debug("Data validation successful")
    except (ValueError, TypeError) as e:
        app.logger.error(f"Error during data validation: {e}")
        return jsonify({'error': str(e)}), 400

    # Calculate metrics
    try:
        app.logger.info("Calculating metrics...")
        metrics = calculate_metrics(data)
    except InternalServerError as e:
        app.logger.error(str(e))
        return jsonify({'error': str(e)}), 500

    # Add timestamp and renewal date (you can replace these with actual values from your application)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    renewal_date = current_time

    # Return response
    app.logger.info("Returning response")
    return jsonify({
        'timestamp': current_time,
        'renewal_date': renewal_date,
        'metrics': metrics
    }), 200


# Mock definitions for app logger and exceptions (you should replace these with your actual setup)
class InternalServerError(Exception):
    pass


app = {
    "logger": {
        "info": lambda message: print(f"INFO: {message}"),
        "debug": lambda message: print(f"DEBUG: {message}"),
        "error": lambda message: print(f"ERROR: {message}")
    }
}

rate_limit_counter = {}
RATE_LIMIT_THRESHOLD = 10
RATE_LIMIT_PERIOD = 60  # seconds

# Test code

from collections import defaultdict
from threading import Lock
import time


def get_rate_limit_status(ip_address) -> tuple[bool, int]:
    global request_counts

    with lock:
        current_time = time.time()

        # Remove expired requests from the dictionary
        for ip, timestamp in list(request_counts.items()):
            if current_time - timestamp > 60:
                del request_counts[ip]

        # Check and update the request count for the given IP address
        if request_counts[ip_address] >= 5:
            return False, request_counts[ip_address]
        else:
            request_counts[ip_address] += 1
            return True, request_counts[ip_address]


# Example usage
request_counts = defaultdict(int)
lock = Lock()

from flask import Flask, jsonify
import logging
import os
import psutil


def get_system_metrics():
    try:
        # Get memory usage statistics
        mem_stats = psutil.virtual_memory()

        # Get system uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])

        # Calculate uptime in a human-readable format (days, hours, minutes)
        days = int(uptime_seconds / 86400)
        hours = int((uptime_seconds % 86400) / 3600)
        minutes = int((uptime_seconds % 3600) / 60)

        # Return metrics as a dictionary
        return {
            "memory_total": mem_stats.total,
            "memory_used": mem_stats.used,
            "memory_percent": mem_stats.percent,
            "system_uptime_days": days,
            "system_uptime_hours": hours,
            "system_uptime_minutes": minutes
        }
    except psutil.AccessDenied as e:
        logging.error(f"Access denied while fetching system metrics: {e}")
        return {"error": "Failed to fetch system metrics"}, 500
    except PermissionError as e:
        logging.error(f"Permission error while fetching system metrics: {e}")
        return {"error": "Failed to fetch system metrics"}, 500
    except OSError as e:
        logging.error(f"OS error while fetching system metrics: {e}")
        return {"error": "Failed to fetch system metrics"}, 500


@app.route('/metrics', methods=['GET'])
def get_metrics_route():
    try:
        metrics = get_system_metrics()
        print("System Metrics Retrieved:", metrics)  # Debugging
        return jsonify(metrics)
    except (psutil.AccessDenied, PermissionError, OSError) as e:
        logging.error(f"Error handling GET /metrics: {e}")
        print(f"Internal Server Error: {e}")  # Debugging
        return jsonify({"error": "Internal Server Error"}), 500


# Test code (local test server only)
print("Flask application is running")
app = Flask(__name__)
logging.basicConfig(level=logging.ERROR)

from flask import Flask, jsonify
from flask import request
import psutil
import psutil  # For system metrics
import time

app = Flask(__name__)


def get_system_metrics():
    return {
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        # Add more metrics as needed
    }


def is_over_rate_limit(ip):
    if ip not in rate_limit_store:
        rate_limit_store[ip] = {'count': 0, 'last_reset_time': time.time()}

    now = time.time()
    elapsed_time = now - rate_limit_store[ip]['last_reset_time']
    if elapsed_time > RATE_LIMIT_INTERVAL:
        rate_limit_store[ip] = {'count': 1, 'last_reset_time': now}
        return False

    if rate_limit_store[ip]['count'] < REQUEST_LIMIT:
        rate_limit_store[ip]['count'] += 1
        return False

    return True


@app.route('/api/health', methods=['GET'])
def health_check():
    client_ip = request.remote_addr

    if is_over_rate_limit(client_ip):
        return jsonify({'message': 'Rate limit exceeded'}), 503

    metrics = get_system_metrics()

    return jsonify(metrics)


rate_limit_store = {}
REQUEST_LIMIT = 10
RATE_LIMIT_INTERVAL = 60  # 60 seconds


def is_over_rate_limit(ip):
    if ip not in rate_limit_store:
        rate_limit_store[ip] = {'count': 0, 'last_reset_time': time.time()}

    now = time.time()
    elapsed_time = now - rate_limit_store[ip]['last_reset_time']
    if elapsed_time > RATE_LIMIT_INTERVAL:
        rate_limit_store[ip] = {'count': 1, 'last_reset_time': now}
        return False

    if rate_limit_store[ip]['count'] < REQUEST_LIMIT:
        rate_limit_store[ip]['count'] += 1
        return False

    return True


def get_system_metrics():
    return {
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        # Add more metrics as needed
    }


@app.route('/api/health', methods=['GET'])
def health_check():
    client_ip = request.remote_addr

    if is_over_rate_limit(client_ip):
        return jsonify({'message': 'Rate limit exceeded'}), 503

    metrics = get_system_metrics()

    return jsonify(metrics)


app = Flask(__name__)
rate_limit_store = {}
REQUEST_LIMIT = 10
RATE_LIMIT_INTERVAL = 60  # 60 seconds

from flask import Flask, jsonify, request
from functools import wraps
import time  # Import time module to avoid undefined variable error


def require_json(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return handle_bad_request('Invalid content type. Expecting application/json.')

        return f(*args, **kwargs)

    return decorated


def validate_data(required_fields, optional_fields=None, data=None):
    required_fields = required_fields or []
    optional_fields = optional_fields or []

    if not data:
        return handle_bad_request('Request body is missing.')

    for field in required_fields:
        if field not in data:
            return handle_bad_request(f'Missing field: {field}')
        if data[field] is None:
            return handle_bad_request(f'Null value not allowed for field: {field}')

    for key, value in data.items():
        if key not in required_fields and key not in optional_fields:
            return handle_validation_error(f'Invalid field: {key}')

    # Perform additional data validation logic here

    return None


def rate_limit(limit, period):
    request_counter = {}

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            remote_addr = request.remote_addr
            now = int(time.time())

            if remote_addr not in request_counter:
                request_counter[remote_addr] = [{'timestamp': now, 'count': 1}]
                return f(*args, **kwargs)

            request_log = request_counter[remote_addr]

            # Iterate from the latest log to avoid modifying list while iterating
            for log in reversed(request_log):
                diff = now - log['timestamp']

                if diff >= period:
                    break

                log['count'] += 1
                return f(*args, **kwargs)
            else:
                log['timestamp'] = now
                log['count'] += 1

            if request_log[-1]['count'] > limit:
                return handle_rate_limit(f'Rate limit exceeded. Try again later.')

            return f(*args, **kwargs)

        return decorated

    return decorator


def calculate_safely(num1, num2):
    try:
        # Perform some calculations that might fail (division by zero, overflow etc.)
        result = num1 / num2
        return result
    except ZeroDivisionError as e:  # Catch specific exception
        return handle_server_error(str(e))
    except OverflowError as e:  # Catch specific exception
        return handle_server_error(str(e))


# Define the error handling functions
def handle_bad_request(message):
    print(f"Bad Request Error: {message}")  # Debugging print
    return jsonify({'error': message}), 400


def handle_validation_error(message):
    print(f"Validation Error: {message}")  # Debugging print
    return jsonify({'error': message}), 422


def handle_rate_limit(message):
    print(f"Rate Limit Exceeded: {message}")  # Debugging print
    return jsonify({'error': message}), 429


def handle_server_error(message):
    print(f"Server Error: {message}")  # Debugging print
    return jsonify({'error': message}), 500


# Flask App Setup
app = Flask(__name__)


@app.route('/validate', methods=['POST'])
@require_json
def validate_endpoint():
    data = request.get_json()
    result = validate_data(required_fields=['key'], optional_fields=None, data=data)
    if isinstance(result, tuple):
        status_code = result[1]
        response_data = {'error': str(result[0])}
    else:
        status_code = 200
        response_data = {'message': 'Validation successful'}
    return jsonify(response_data), status_code


@app.route('/calculate', methods=['GET'])
def calculate_endpoint():
    num1 = float(request.args.get('num1', default=0, type=float))
    num2 = float(request.args.get('num2', default=0, type=float))
    result = calculate_safely(num1, num2)
    if isinstance(result, tuple):
        status_code = result[1]
        response_data = {'error': str(result[0])}
    else:
        status_code = 200
        response_data = {'result': result}
    return jsonify(response_data), status_code