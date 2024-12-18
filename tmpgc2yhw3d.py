import json

def validate_request_format(request_data) -> tuple[bool, str]:
    try:
        # Step 1: Parse JSON data
        data = json.loads(request_data)
        
        # Step 2: Check required fields and their types
        if 'email' not in data or not isinstance(data['email'], str):
            return False, "Missing or invalid email field"
        if 'age' not in data or not isinstance(data['age'], int) or data['age'] < 0:
            return False, "Missing or invalid age field"
        if 'subscription_tier' not in data or not isinstance(data['subscription_tier'], str):
            return False, "Missing or invalid subscription tier field"
        if 'user_data' not in data or not isinstance(data['user_data'], dict):
            return False, "Missing or invalid user data field"
        
        # Step 3: If all checks pass
        return True, ""
    
    except json.JSONDecodeError:
        # Handle malformed JSON
        return False, "Malformed JSON"

# Example usage
request_data = '{"email": "user@example.com", "age": 25, "subscription_tier": "premium", "user_data": {}}'
is_valid, error_msg = validate_request_format(request_data)
print(f"Is Valid: {is_valid}, Error Message: '{error_msg}'")