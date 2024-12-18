import json

def validate_request_format(request_data):
    try:
        # Step 1: Parse JSON data
        data = json.loads(request_data)
        print(f"Parsed JSON Data: {data}")
    except json.JSONDecodeError as e:
        # Malformed JSON
        print(f"JSON Decode Error: {e}")
        return (False, "400: Malformed JSON")

    # Step 2: Check for required fields
    required_fields = ["email", "age", "subscription_tier", "user_data"]
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        print(f"Missing Fields: {missing_fields}")
        return (False, f"400: Missing fields - {', '.join(missing_fields)}")

    # Step 3: Validate data types
    if not isinstance(data["email"], str):
        print("Invalid type for 'email'")
        return (False, "422: Invalid data type for 'email' - expected string")
    
    if not isinstance(data["age"], int):
        print("Invalid type for 'age'")
        return (False, "422: Invalid data type for 'age' - expected integer")
    
    if not isinstance(data["subscription_tier"], str):
        print("Invalid type for 'subscription_tier'")
        return (False, "422: Invalid data type for 'subscription_tier' - expected string")
    
    if not isinstance(data["user_data"], dict):
        print("Invalid type for 'user_data'")
        return (False, "422: Invalid data type for 'user_data' - expected dictionary")

    # Step 4: All checks passed
    return (True, "")

# Example usage:
request_data = '{"email": "test@example.com", "age": 30, "subscription_tier": "basic", "user_data": {}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Validation Result: {is_valid}, Error Message: {error_msg}")