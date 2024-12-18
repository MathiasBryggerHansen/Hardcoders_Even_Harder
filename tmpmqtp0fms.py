def validate_request_format(request_data) -> tuple[bool, str]:
    # Debugging print to expose the input data
    print(f"Received request data: {request_data}")
    
    # Step 1: Check if the request data is a dictionary
    if not isinstance(request_data, dict):
        print("Error: Request data is not a dictionary")
        return False, "400 - Malformed JSON"
    
    # Step 2: Verify the presence of required fields
    required_fields = ["email", "age", "subscription_tier", "user_data"]
    for field in required_fields:
        if field not in request_data or request_data[field] is None:
            print(f"Error: Missing or null field '{field}'")
            return False, "400 - Missing or null fields"
    
    # Step 3: Validate data types for each field
    try:
        # Validate 'email'
        if not isinstance(request_data["email"], str):
            raise ValueError("Email must be a string")
        
        # Validate 'age'
        if not isinstance(request_data["age"], int):
            raise ValueError("Age must be an integer")
        
        # Validate 'subscription_tier'
        if not isinstance(request_data["subscription_tier"], str):
            raise ValueError("Subscription tier must be a string")
        
        # Validate 'user_data'
        if not isinstance(request_data["user_data"], dict):
            raise ValueError("User data must be a dictionary")
    
    except ValueError as e:
        print(f"Error: {str(e)}")
        return False, "422 - Invalid data types"
    
    # If all checks pass
    print("Validation successful")
    return True, ""

# Test cases
test_data_1 = {
    "email": "example@example.com",
    "age": 30,
    "subscription_tier": "premium",
    "user_data": {"name": "John Doe"}
}

test_data_2 = {
    "email": "example@example.com",
    "age": "thirty",  # Invalid age type
    "subscription_tier": "premium",
    "user_data": {"name": "John Doe"}
}

test_data_3 = {
    "email": None,
    "age": 30,
    "subscription_tier": "premium",
    "user_data": {"name": "John Doe"}
}

test_data_4 = {
    "email": "example@example.com",
    "age": 30,
    "subscription_tier": "premium"
    # Missing 'user_data'
}

test_cases = [test_data_1, test_data_2, test_data_3, test_data_4]

for i, data in enumerate(test_cases):
    print(f"Test case {i+1}:")
    is_valid, error_msg = validate_request_format(data)
    print(f"Result: {is_valid}, Error Message: {error_msg}\n")