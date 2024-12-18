import json

def validate_request_format(request_data: str) -> tuple[bool, str]:
    # Step 1: Parse the JSON data
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError as e:
        print(f"Malformed JSON received: {e}")
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

# Test code
def test_validate_request_format():
    # Test case 1: Valid request
    request_valid = '{"email": "test@example.com", "age": 30, "subscription_tier": "basic", "user_data": {"name": "John"}}'
    result = validate_request_format(request_valid)
    print(f"Test case 1 - Expected (True, ''), Got: {result}")

    # Test case 2: Malformed JSON
    request_malformed = '{"email": "test@example.com", "age": 30, "subscription_tier": "basic", "user_data": {"name": "John"'
    result = validate_request_format(request_malformed)
    print(f"Test case 2 - Expected (False, '400 Bad Request - Malformed JSON'), Got: {result}")

    # Test case 3: Missing fields
    request_missing_fields = '{"email": "test@example.com", "age": 30}'
    result = validate_request_format(request_missing_fields)
    print(f"Test case 3 - Expected (False, '400 Bad Request - Missing fields: subscription_tier, user_data'), Got: {result}")

    # Test case 4: Invalid data types
    request_invalid_types = '{"email": 123, "age": "thirty", "subscription_tier": true, "user_data": "not a dict"}'
    result = validate_request_format(request_invalid_types)
    print(f"Test case 4 - Expected (False, '422 Unprocessable Entity - Invalid email data type'), Got: {result}")

# Run tests
test_validate_request_format()