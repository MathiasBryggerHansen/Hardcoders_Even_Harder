import json

def validate_request_format(request_data) -> tuple[bool, str]:
    try:
        # Step 1: Parse the JSON data
        data = json.loads(request_data)
        print("Parsed JSON data:", data)  # Debugging print
        
        # Step 2: Check for required fields
        required_fields = ['email', 'age', 'subscription_tier', 'user_data']
        for field in required_fields:
            if field not in data or data[field] is None:
                error_msg = f"400: Missing or null value for '{field}'"
                print(error_msg)  # Debugging print
                return False, error_msg
        
        # Step 3: Validate data types
        if not isinstance(data['email'], str):
            error_msg = "422: 'email' must be a string"
            print(error_msg)  # Debugging print
            return False, error_msg
        if not isinstance(data['age'], int):
            error_msg = "422: 'age' must be an integer"
            print(error_msg)  # Debugging print
            return False, error_msg
        if not isinstance(data['subscription_tier'], str):
            error_msg = "422: 'subscription_tier' must be a string"
            print(error_msg)  # Debugging print
            return False, error_msg
        
        # Step 4: Return success if all checks pass
        print("Validation successful")  # Debugging print
        return True, ''
    
    except json.JSONDecodeError:
        # Handle malformed JSON
        error_msg = "400: Malformed JSON"
        print(error_msg)  # Debugging print
        return False, error_msg

# Example usage
request_data = '{"email": "user@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"key": "value"}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is valid: {is_valid}, Error message: '{error_msg}'")