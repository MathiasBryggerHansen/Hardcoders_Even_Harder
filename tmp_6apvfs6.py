import json

def validate_request_format(request_data):
    try:
        # Step 1: Parse JSON data
        data = json.loads(request_data)
        print(f"Parsed JSON: {data}")
    except json.JSONDecodeError:
        print("Error: Malformed JSON")
        return (False, "Malformed JSON")

    # Step 2: Check for required fields
    required_fields = ['email', 'age', 'subscription_tier', 'user_data']
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        print(f"Error: Missing fields {missing_fields}")
        return (False, "400 Bad Request")

    # Step 3: Validate data types
    if not isinstance(data['email'], str):
        print("Error: 'email' must be a string")
        return (False, "Invalid data types")
    
    if not isinstance(data['age'], int):
        print("Error: 'age' must be an integer")
        return (False, "Invalid data types")
    
    if not isinstance(data['subscription_tier'], str):
        print("Error: 'subscription_tier' must be a string")
        return (False, "Invalid data types")
    
    # Assume user_data can be any type, but here we check if it's a dictionary
    if not isinstance(data['user_data'], dict):
        print("Error: 'user_data' must be a dictionary")
        return (False, "Invalid data types")

    # Step 4: Return the result
    print("Validation successful")
    return (True, "")

# Example usage:
# request_data = '{"email": "test@example.com", "age": 30, "subscription_tier": "premium", "user_data": {}}'
# is_valid, error_msg = validate_request_format(request_data)
# print(is_valid, error_msg)