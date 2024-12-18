import json

def validate_request_format(request_data: str) -> tuple[bool, str]:
    # Step 1: Parse the JSON data
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError:
        print("Malformed JSON received")
        return (False, "400 Bad Request - Malformed JSON")

    # Step 2: Check for required fields
    required_fields = ["email", "age", "subscription_tier", "user_data"]
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        print(f"Missing fields: {', '.join(missing_fields)}")
        return (False, f"400 Bad Request - Missing fields: {', '.join(missing_fields)}")

    # Step 3: Validate data types
    if not isinstance(data['email'], str):
        print("Invalid email data type")
        return (False, "422 Unprocessable Entity - Invalid email data type")
    
    if not isinstance(data['age'], int):
        print("Invalid age data type")
        return (False, "422 Unprocessable Entity - Invalid age data type")
    
    if not isinstance(data['subscription_tier'], str):
        print("Invalid subscription tier data type")
        return (False, "422 Unprocessable Entity - Invalid subscription tier data type")
    
    if not isinstance(data['user_data'], dict):
        print("Invalid user_data data type")
        return (False, "422 Unprocessable Entity - Invalid user_data data type")

    # Step 4: Return the result
    print("Request is valid")
    return (True, "")

# Example usage:
# request_data = '{"email": "test@example.com", "age": 30, "subscription_tier": "premium", "user_data": {}}'
# print(validate_request_format(request_data))