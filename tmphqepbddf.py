def validate_request_format(request_data):
    try:
        # Parse JSON data
        data = json.loads(request_data)
        
        # Required fields and their expected types
        required_fields = {
            "email": str,
            "age": int,
            "subscription_tier": str,
            "user_data": dict
        }
        
        # Check for missing or null fields
        for field, expected_type in required_fields.items():
            if field not in data:
                return False, f"Missing required field: {field}"
            
            value = data[field]
            if value is None:
                return False, f"Field '{field}' cannot be null"
            
            # Check for invalid data types
            if not isinstance(value, expected_type):
                return False, f"Invalid data type for '{field}': {expected_type.__name__}, got {type(value).__name__}"
        
        # All checks passed
        return True, "Request is valid"
    
    except json.JSONDecodeError:
        return False, "Malformed JSON"

# Example usage
request_data = '{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"id": 123}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is Valid: {is_valid}, Error Msg: '{error_msg}'")