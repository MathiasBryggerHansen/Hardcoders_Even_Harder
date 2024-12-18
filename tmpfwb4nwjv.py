import json

def validate_request_format(request_data):
    try:
        # Step 1: Parse the JSON data
        data = json.loads(request_data)
        print("Parsed JSON:", data)  # Debugging print
        
        # Step 2: Check for required fields
        required_fields = ['email', 'age', 'subscription_tier', 'user_data']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            error_msg = f"Missing fields: {', '.join(missing_fields)}"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        # Step 3: Validate data types
        if not isinstance(data['email'], str):
            error_msg = "Invalid data type for 'email': expected string"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['age'], int):
            error_msg = "Invalid data type for 'age': expected integer"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['subscription_tier'], str):
            error_msg = "Invalid data type for 'subscription_tier': expected string"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        if not isinstance(data['user_data'], dict):
            error_msg = "Invalid data type for 'user_data': expected dictionary"
            print("Error:", error_msg)  # Debugging print
            return (False, error_msg)
        
        # Step 4: Return the result if all checks pass
        return (True, "")
    
    except json.JSONDecodeError:
        # Handle malformed JSON
        error_msg = "Malformed JSON"
        print("Error:", error_msg)  # Debugging print
        return (False, error_msg)