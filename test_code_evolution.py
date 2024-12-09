import unittest
from error_handler import enhance_error
from code_evolution import CodeEvolutionHandler


class TestCodeEvolution(unittest.TestCase):
    def setUp(self):
        self.handler = CodeEvolutionHandler()

    def test_basic_fibonacci(self):
        result = CodeEvolutionHandler.process_with_reflection("Create a function that returns the nth Fibonacci number. "
                                         "Function should be called fib and take one parameter n.")
        self.assertIsNotNone(result)
        namespace = {}
        print(result)
        exec(result, namespace)
        self.assertTrue('fib' in namespace)
        self.assertEqual(namespace['fib'](5), 3)

    def test_history_retention(self):
        handler = CodeEvolutionHandler(history_size=3)
        handler.add_attempt("def f(): pass", "Error 1")
        handler.add_attempt("def f(): return 1", "Error 2")
        handler.add_attempt("def f(): return 2", "Error 3")
        handler.add_attempt("def f(): return 3", "Error 4")
        self.assertEqual(len(handler.history), 3)

    def test_diff_generation(self):
        handler = CodeEvolutionHandler()
        handler.add_attempt("def f():\n    pass", "Error 1")
        handler.add_attempt("def f():\n    return 1", "Error 2")
        self.assertIn("return 1", handler.history[-1].diff_from_previous)

    def test_complex_operations(self):
        # Test matrix operations with proper numpy import
        result = CodeEvolutionHandler.process_with_reflection("""
            Create a function that:
            1. Takes a matrix (2D list)
            2. Validates it's square
            3. Calculates determinant
            4. Uses numpy
            Name it matrix_det
        """)

        # Create isolated namespace with numpy import
        namespace = {}
        exec("import numpy as np\n" + result, namespace)

        # Test cases
        test_cases = [
            ([[1, 2], [3, 4]], -2),  # 2x2 matrix
            ([[1]], 1),  # 1x1 matrix
            ([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]], 0)  # 3x3 matrix
        ]

        for matrix, expected in test_cases:
            # Use assertAlmostEqual for floating-point comparison
            self.assertAlmostEqual(namespace['matrix_det'](matrix), expected, places=10)

        # Test validation
        invalid_matrix = [[1, 2], [3]]  # Non-square matrix
        with self.assertRaises(ValueError):
            namespace['matrix_det'](invalid_matrix)

    def test_error_propagation(self):
        # Verify error details are fed back to model
        evolution = CodeEvolutionHandler()
        evolution.add_attempt("def f(): return x", "NameError: name 'x' is not defined")
        formatted = evolution.format_history_for_prompt()
        self.assertIn("NameError", formatted)



if __name__ == '__main__':
    unittest.main()
