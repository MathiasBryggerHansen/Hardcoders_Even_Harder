    import json

def validate_request_format(request_data):
    
    try:
        # Step 1: Parse the JSON data
        data = json.loads(request_data)
        print("Parsed JSON data:", data)  # Debugging print
        
        # Step 2: Check for required fields
        required_fields = ['email', 'age', 'subscription_tier', 'user_data']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            error_msg = f"Missing or null fields: {', '.join(missing_fields)}"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        # Step 3: Validate data types
        if not isinstance(data['email'], str):
            error_msg = "Invalid data type for 'email': must be a string"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['age'], int):
            error_msg = "Invalid data type for 'age': must be an integer"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['subscription_tier'], str):
            error_msg = "Invalid data type for 'subscription_tier': must be a string"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['user_data'], dict):
            error_msg = "Invalid data type for 'user_data': must be a dictionary"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        # Step 4: Return the result if all checks pass
        return (True, "")
    
    except json.JSONDecodeError:
        error_msg = "Malformed JSON data"
        print("Error:", error_msg)  # Debugging print
        return (False, error_msg)

# Example usage
request_data = '{"email": "test@example.com", "age": 30, "subscription_tier": "basic", "user_data": {}}'
print(validate_request_format(request_data))