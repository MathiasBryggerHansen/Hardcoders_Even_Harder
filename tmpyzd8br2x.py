import json

def validate_request_format(request_data):
    try:
        # Step 1: Convert request data to a dictionary if it's not already one
        data_dict = json.loads(request_data)
        
    except json.JSONDecodeError:
        # Malformed JSON -> Return (False, "400 Bad Request")
        return False, "400 Bad Request"
    
    required_fields = {'email', 'age', 'subscription_tier', 'user_data'}
    data_dict_keys = set(data_dict.keys())
    
    # Step 2: Check for missing or null fields
    if not required_fields.issubset(data_dict_keys):
        return False, "400 Bad Request"
    
    # Step 3: Validate data types
    validation_errors = []
    
    if not isinstance(data_dict['email'], str) or not data_dict['email']:
        validation_errors.append("Email must be a non-empty string")
    
    if not isinstance(data_dict['age'], int) or data_dict['age'] <= 0:
        validation_errors.append("Age must be a positive integer")
    
    if not isinstance(data_dict['subscription_tier'], str):
        validation_errors.append("Subscription tier must be a string")
    
    # Step 4: Return result based on validations
    if validation_errors:
        error_msg = ", ".join(validation_errors)
        return False, f"422 Unprocessable Entity - {error_msg}"
    
    # If all checks pass, the request is valid
    return True, "Request is valid"