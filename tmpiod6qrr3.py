import json

def validate_request_format(request_data) -> tuple[bool, str]:
    # Step 1: Parse JSON data
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError as e:
        print(f"Malformed JSON: {e}")
        return (False, "400 Bad Request: Malformed JSON")

    # Step 2: Check for required fields
    required_fields = ["email", "age", "subscription_tier", "user_data"]
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        error_msg = f"400 Bad Request: Missing or null fields: {', '.join(missing_fields)}"
        print(error_msg)
        return (False, error_msg)

    # Step 3: Validate data types
    if not isinstance(data["email"], str):
        error_msg = "422 Unprocessable Entity: 'email' must be a string"
        print(error_msg)
        return (False, error_msg)
    
    if not isinstance(data["age"], int):
        error_msg = "422 Unprocessable Entity: 'age' must be an integer"
        print(error_msg)
        return (False, error_msg)
    
    if not isinstance(data["subscription_tier"], str):
        error_msg = "422 Unprocessable Entity: 'subscription_tier' must be a string"
        print(error_msg)
        return (False, error_msg)
    
    if not isinstance(data["user_data"], dict):
        error_msg = "422 Unprocessable Entity: 'user_data' must be a dictionary"
        print(error_msg)
        return (False, error_msg)

    # Step 4: All checks passed
    return (True, "")

# Example usage:
# request_data = '{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": {}}'
# print(validate_request_format(request_data))