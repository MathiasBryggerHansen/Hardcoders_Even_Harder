import unittest
import tempfile
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from code_evolution import CodeEvolutionHandler
from static_analysis import EnhancedErrorHandler

class TestWebAppGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.template_dir = os.path.join(cls.temp_dir, 'templates')
        os.makedirs(cls.template_dir, exist_ok=True)
        cls.handler = CodeEvolutionHandler()
        cls.error_handler = EnhancedErrorHandler()
        cls.app = cls._execute_flask_app(cls.get_requirements())

    def setUp(self):
        self.client = self.app.test_client()
        if hasattr(self.app, '_request_counts'):
            self.app._request_counts.clear()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'handler'):
            cls.handler.cleanup()
        if os.path.exists(cls.temp_dir):
            import shutil
            shutil.rmtree(cls.temp_dir)

    @classmethod
    def _execute_flask_app(cls, requirements: str):
        """Helper method to generate and execute Flask app code."""
        result = None
        try:
            # Generate the code first
            result = cls.handler.process_with_reflection(requirements)
            if result is None:
                raise RuntimeError("Failed to generate code")

            # Extract all requirements before any execution
            all_requirements = ['flask']  # Start with flask as base requirement
            additional_reqs = cls.handler.extract_requirements(result)
            if additional_reqs:
                all_requirements.extend(additional_reqs)

            # Install all requirements at once
            ret_code, stdout, stderr = cls.handler.install_requirements(all_requirements)
            if ret_code != 0:
                raise RuntimeError(f"Failed to install requirements: {stderr}")

            # Create namespace and execute code after all requirements are installed
            namespace = {'__name__': '__main__'}
            exec('from flask import Flask, request, jsonify', namespace)
            exec(result, namespace)

            app = namespace.get('app')
            if app is None:
                raise ValueError("No Flask app was created")

            app.config['TESTING'] = True
            app.config['SERVER_NAME'] = 'localhost'
            print("APP")
            return app

        except Exception as e:
            print(cls.error_handler.enhance_error(e, result))
            raise RuntimeError(f"Flask app generation/execution failed: {cls.error_handler.enhance_error(e, result)}")



    """Create a Flask application for WINDOWS with these requirements:
                1. Create route '/api/process' that:
                   - Accepts POST requests with JSON data
                   - Requires fields: 'email', 'age', 'subscription_tier', 'user_data'
                   - 'user_data' must be a nested JSON object with required fields:
                     * 'preferences' (dict with 'notifications' boolean and 'theme' string)
                     * 'payment_info' (dict with 'method' and 'currency')
                     * 'usage_metrics' (array of numbers, length 3-10)
                   - Validates email format (must be company domain @validcompany.com)
                   - Age must be between 18 and 100
                   - subscription_tier must be one of: ['basic', 'pro', 'enterprise']
                   - Returns 422 with proper error message if validation fails
                   - Returns processed data with calculated fields:
                     * price based on tier: basic($10), pro($25), enterprise($50)
                     * risk_score: calculated as (age * usage_metrics_average / 10)
                     * premium_multiplier: 1.5 if payment_method is 'crypto'
                   - Adds processing timestamp
                   - Calculates renewal_date as 1 year from processing

                2. The following rules ***MUST*** be satisfied:
                   - JSON parsing errors (malformed JSON) -> 400
                   - Missing or null fields -> 400
                   - Invalid data types -> 422
                   - Division by zero in calculations -> 500
                   - Integer overflow scenarios -> 500
                   - Array index out of bounds -> 500
                   - Type conversion errors -> 422
                   - Rate limiting (max 5 requests per minute per IP) -> 429
                   - Concurrent request handling

                3. Add route '/api/health' that:
                   - Returns system status
                   - Includes current rate limit counts
                   - Memory usage stats
                   - Uptime"""

    @staticmethod
    def get_requirements() -> list:
        function_descriptions = [
            "validate_request_format(request_data) -> tuple[bool, str] - Verify JSON data has required fields (email, age, subscription_tier, user_data) with correct data types. Handle: malformed JSON -> 400, missing/null fields -> 400, invalid data types -> 422. Return (is_valid, error_msg)",

"validate_user_data(user_data) -> tuple[bool, str] - Check user_data contains valid preferences (notifications bool, theme str), payment_info (method, currency), and usage_metrics (array[3-10] of numbers). Handle: array index out of bounds -> 500, type conversion errors -> 422. Return (is_valid, error_msg)",

"validate_business_rules(email, age, subscription_tier) -> tuple[bool, str] - Validate email is @validcompany.com, age is 18-100, subscription_tier in ['basic', 'pro', 'enterprise']. Handle: type conversion errors -> 422. Return (is_valid, error_msg)",

"calculate_metrics(age, usage_metrics, payment_method, subscription_tier) -> dict - Calculate price (basic:$10, pro:$25, enterprise:$50), risk_score (age * avg_usage / 10), premium_multiplier (1.5 if crypto). Handle: division by zero -> 500, integer overflow -> 500. Return calculated metrics dict",

"process_request() -> Response - Main /api/process POST handler: check rate limit (429 if exceeded), validate data (400/422 for validation fails), calculate metrics (500 for calculation errors), add timestamp and renewal_date, return appropriate HTTP response",

"get_rate_limit_status(ip_address) -> tuple[bool, int] - Track and check if IP exceeded 5 requests/minute, return (is_allowed, current_count). Handle concurrent access to rate limit data",

"get_system_metrics() -> dict - Get current memory usage and system uptime statistics. Handle potential OS-level errors -> 500",

"health_check() -> Response - Handle /api/health GET requests: return system metrics and rate limit counts. Handle service unavailability -> 503",

"Error handlers: handle_bad_request() -> 400 for malformed JSON/missing/null fields, handle_validation_error() -> 422 for invalid data types/values, handle_rate_limit() -> 429 for rate exceeded, handle_server_error() -> 500 for calculation/overflow/division errors"
            ]
        return function_descriptions
    @staticmethod
    def get_valid_data():
        return {
            "email": "test@validcompany.com",
            "age": 25,
            "subscription_tier": "pro",
            "user_data": {
                "preferences": {
                    "notifications": True,
                    "theme": "dark"
                },
                "payment_info": {
                    "method": "crypto",
                    "currency": "USD"
                },
                "usage_metrics": [1.0, 2.0, 3.0, 4.0]
            }
        }

    def test_successful_request(self):
        response = self.client.post('/api/process', json=self.get_valid_data())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        required_fields = {'price', 'risk_score', 'premium_multiplier', 'processing_timestamp', 'renewal_date'}
        self.assertTrue(all(field in data for field in required_fields))
        self.assertEqual(data['price'], 25)
        self.assertEqual(data['premium_multiplier'], 1.5)

        try:
            timestamp = datetime.fromisoformat(data['processing_timestamp'].replace('Z', '+00:00'))
            renewal = datetime.fromisoformat(data['renewal_date'].replace('Z', '+00:00'))
            self.assertGreater(renewal, timestamp)
            self.assertAlmostEqual((renewal - timestamp).days, 365, delta=1)
        except ValueError:
            self.fail("Invalid datetime format")

    def test_validation_errors(self):
        valid_data = self.get_valid_data()
        test_cases = [
            ("missing_required_field", {"email": "test@validcompany.com"}, 400),
            ("null_field", {**valid_data, "age": None}, 400),
            ("invalid_email", {**valid_data, "email": "test@other.com"}, 422),
            ("invalid_age_low", {**valid_data, "age": 15}, 422),
            ("invalid_age_high", {**valid_data, "age": 101}, 422),
            ("invalid_subscription", {**valid_data, "subscription_tier": "invalid"}, 422),
            ("invalid_notifications", {
                **valid_data,
                "user_data": {
                    **valid_data["user_data"],
                    "preferences": {"notifications": "not-boolean", "theme": "dark"}
                }
            }, 422),
            ("invalid_usage_metrics_length", {
                **valid_data,
                "user_data": {
                    **valid_data["user_data"],
                    "usage_metrics": [1, 2]
                }
            }, 422)
        ]

        for test_name, data, expected_status in test_cases:
            with self.subTest(test_name):
                response = self.client.post('/api/process', json=data)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn("error", response.get_json())

    def test_server_errors(self):
        valid_data = self.get_valid_data()
        test_cases = [
            ("division_by_zero", {
                **valid_data,
                "user_data": {
                    **valid_data["user_data"],
                    "usage_metrics": [0, 0, 0]
                }
            }),
            ("integer_overflow", {**valid_data, "age": 2 ** 31})
        ]

        for test_name, data in test_cases:
            with self.subTest(test_name):
                response = self.client.post('/api/process', json=data)
                self.assertEqual(response.status_code, 500)
                self.assertIn("error", response.get_json())

    def test_rate_limiting(self):
        valid_data = self.get_valid_data()

        def reset_rate_limit():
            if hasattr(self.app, 'rate_limits'):
                for ip in self.app.rate_limits:
                    self.app.rate_limits[ip]['last_reset'] = time.time() - 61

        for _ in range(5):
            response = self.client.post('/api/process', json=valid_data)
            self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/process', json=valid_data)
        self.assertEqual(response.status_code, 429)
        self.assertIn("error", response.get_json())

        reset_rate_limit()
        response = self.client.post('/api/process', json=valid_data)
        self.assertEqual(response.status_code, 200)

    def test_concurrent_requests(self):
        valid_data = self.get_valid_data()

        def make_request():
            return self.client.post('/api/process', json=valid_data)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            try:
                responses = [f.result(timeout=5) for f in futures]
            except TimeoutError:
                self.fail("Concurrent requests timed out")

        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        self.assertEqual(success_count, 5)
        self.assertEqual(rate_limited_count, 5)

    def test_health_endpoint(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        required_fields = {'status', 'rate_limit_counts', 'memory_usage', 'uptime'}
        self.assertTrue(all(field in data for field in required_fields))

        self.client.post('/api/process', json=self.get_valid_data())
        updated_response = self.client.get('/api/health')
        updated_data = updated_response.get_json()
        self.assertGreater(updated_data['rate_limit_counts'].get('127.0.0.1', 0), 0)

    def test_invalid_json(self):
        response = self.client.post(
            '/api/process',
            data="{'invalid': json}",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

if __name__ == '__main__':
    unittest.main()
