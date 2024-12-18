import json

def validate_request_format(request_data):
    try:
        # Step 1: Parse the JSON data
        parsed_data = json.loads(request_data)
        print("Parsed data:", parsed_data)
        
        # Step 2: Check for required fields
        required_fields = ['email', 'age', 'subscription_tier', 'user_data']
        for field in required_fields:
            if field not in parsed_data or parsed_data[field] is None:
                return (False, f"400 Bad Request: Missing or null field '{field}'")
        
        # Step 3: Validate data types
        if not isinstance(parsed_data['email'], str):
            return (False, "422 Unprocessable Entity: 'email' must be a string")
        if not isinstance(parsed_data['age'], int):
            return (False, "422 Unprocessable Entity: 'age' must be an integer")
        if not isinstance(parsed_data['subscription_tier'], str):
            return (False, "422 Unprocessable Entity: 'subscription_tier' must be a string")
        if not isinstance(parsed_data['user_data'], dict):
            return (False, "422 Unprocessable Entity: 'user_data' must be a dictionary")
        
        # Step 4: Return the result
        return (True, '')
    
    except json.JSONDecodeError:
        print("JSONDecodeError: Malformed JSON")
        return (False, "400 Bad Request: Malformed JSON")

# Example usage
request_data = '{"email": "user@example.com", "age": 30, "subscription_tier": "premium", "user_data": {}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is valid: {is_valid}, Error message: '{error_msg}'")