import json

def validate_request_format(request_data) -> tuple[bool, str]:
    # Step 1: Parse the JSON data
    try:
        data = json.loads(request_data)
        print(f"Parsed JSON data: {data}")
    except json.JSONDecodeError:
        return False, "400 Bad Request - Malformed JSON"

    # Step 2: Check for required fields and handle null values
    required_fields = {'email', 'age', 'subscription_tier', 'user_data'}
    if not required_fields.issubset(data):
        return False, "400 Bad Request - Missing or Null Fields"
    
    # Step 3: Validate field types
    errors = []
    if not isinstance(data['email'], str):
        errors.append("422 Unprocessable Entity - 'email' must be a string")
    if not isinstance(data['age'], int) or data['age'] < 0:
        errors.append("422 Unprocessable Entity - 'age' must be a non-negative integer")
    if data['subscription_tier'] not in ['basic', 'premium']:
        errors.append("422 Unprocessable Entity - Invalid subscription tier")
    if not isinstance(data['user_data'], dict):
        errors.append("422 Unprocessable Entity - 'user_data' must be a dictionary")

    # Step 4: Return the validation result
    if errors:
        error_msg = ', '.join(errors)
        return False, error_msg
    else:
        return True, "Request is valid"

# Example usage
request_data = '{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"key": "value"}}'
print(validate_request_format(request_data))

# Test cases
test_cases = [
    ('{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": {"key": "value"}}', True, "Request is valid"),
    ('{"email": null, "age": 30, "subscription_tier": "premium", "user_data": {"key": "value"}}', False, "400 Bad Request - Missing or Null Fields"),
    ('{"email": "example@example.com", "age": -5, "subscription_tier": "premium", "user_data": {"key": "value"}}', False, "422 Unprocessable Entity - 'age' must be a non-negative integer"),
    ('{"email": "example@example.com", "age": 30, "subscription_tier": "invalid", "user_data": {"key": "value"}}', False, "422 Unprocessable Entity - Invalid subscription tier"),
    ('{"email": "example@example.com", "age": 30, "subscription_tier": "premium", "user_data": "not a dictionary"}', False, "422 Unprocessable Entity - 'user_data' must be a dictionary"),
    ('not json', False, "400 Bad Request - Malformed JSON")
]

for i, (request_data, expected_valid, expected_msg) in enumerate(test_cases):
    is_valid, msg = validate_request_format(request_data)
    print(f"Test case {i+1}: {'Passed' if is_valid == expected_valid and msg == expected_msg else 'Failed'}")