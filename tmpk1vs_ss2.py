import json

def validate_request_format(request_data):
    # Parse JSON data
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError:
        print("Malformed JSON")
        return False, "Malformed JSON"
    
    required_fields = {
        "email": str,
        "age": int,
        "subscription_tier": str,
        "user_data": dict
    }
    
    # Check for missing or null fields
    for field, expected_type in required_fields.items():
        print(f"Checking field: {field}")
        if field not in data:
            print(f"Missing required field: {field}")
            return False, f"Missing required field: {field}"
        
        value = data[field]
        if value is None:
            print(f"Field '{field}' cannot be null")
            return False, f"Field '{field}' cannot be null"
        
        # Check for invalid data types
        if not isinstance(value, expected_type):
            print(f"Invalid data type for '{field}': {expected_type.__name__}, got {type(value).__name__}")
            return False, f"Invalid data type for '{field}': {expected_type.__name__}, got {type(value).__name__}"
    
    # All checks passed
    print("Request is valid")
    return True, "Request is valid"

# Example usage
request_data = '{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"id": 123}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is Valid: {is_valid}, Error Msg: '{error_msg}'")

# Test case with missing field
request_data_missing_field = '{"email": "example@example.com", "age": 30, "subscription_tier": "premium"}'
is_valid, error_msg = validate_request_format(request_data_missing_field)
print(f"Is Valid: {is_valid}, Error Msg: '{error_msg}'")

# Test case with invalid data type
request_data_invalid_type = '{"email": "example@example.com", "age": "thirty", "subscription_tier": "premium", "user_data": {"id": 123}}'
is_valid, error_msg = validate_request_format(request_data_invalid_type)
print(f"Is Valid: {is_valid}, Error Msg: '{error_msg}'")