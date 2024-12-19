


    import json

def validate_request_format(request_data):
    try:
        # Step 2: Parse the JSON data
        data = json.loads(request_data)
        
        # Step 3: Check for required fields
        required_fields = {'email', 'age', 'subscription_tier', 'user_data'}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            error_msg = f"Missing fields: {', '.join(missing_fields)}"
            return False, error_msg
        
        # Step 4: Validate data types
        if not isinstance(data['email'], str):
            return False, "Invalid email type. Expected a string."
        if not isinstance(data['age'], int):
            return False, "Invalid age type. Expected an integer."
        if not isinstance(data['subscription_tier'], str):
            return False, "Invalid subscription tier type. Expected a string."
        if not isinstance(data['user_data'], dict):
            return False, "Invalid user data type. Expected a dictionary."
        
        # If all checks pass
        return True, ""
    
    except json.JSONDecodeError:
        # Step 5: Handle malformed JSON
        error_msg = "Malformed JSON"
        return False, error_msg

# Example usage:
request_data = '{"email": "user@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"id": 1}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is valid: {is_valid}, Error msg: '{error_msg}'")
    