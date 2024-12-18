import pytest
from hypothesis import given, strategies as st

class Test_calculate_discount:
    """Tests for calculate_discount generated with Qwen assistance"""

    def test_boundary_0(self):
        """Test: Test with zero price and one item to ensure no discount is applied."""
        result = calculate_discount(**{'price': 0, 'quantity': 1})
        assert pytest.approx(result, rel=1e-2) == 0

    def test_boundary_1(self):
        """Test: Test with zero quantity to ensure no discount is applied."""
        result = calculate_discount(**{'price': 100, 'quantity': 0})
        assert pytest.approx(result, rel=1e-2) == 0

    def test_boundary_2(self):
        """Test: Test with negative price to trigger a ValueError."""
        with pytest.raises(ValueError):
            calculate_discount(**{'price': -1, 'quantity': 5})

    def test_boundary_3(self):
        """Test: Test with negative quantity to trigger a ValueError."""
        with pytest.raises(ValueError):
            calculate_discount(**{'price': 50, 'quantity': -2})

    def test_edge_4(self):
        """Test: Test with quantity just below the bulk discount threshold to ensure no discount is applied."""
        result = calculate_discount(**{'price': 100, 'quantity': 9})
        assert pytest.approx(result, rel=1e-2) == 85.5

    def test_edge_5(self):
        """Test: Test with quantity at the bulk discount threshold to ensure 10% discount is applied."""
        result = calculate_discount(**{'price': 100, 'quantity': 10})
        assert pytest.approx(result, rel=1e-2) == 90.0

    def test_normal_6(self):
        """Test: Test with a typical usage scenario where medium discount is applied."""
        result = calculate_discount(**{'price': 50, 'quantity': 6})
        assert pytest.approx(result, rel=1e-2) == 47.25

    def test_normal_7(self):
        """Test: Test with typical usage scenario without premium member discount."""
        result = calculate_discount(**{'price': 100, 'quantity': 3})
        assert pytest.approx(result, rel=1e-2) == 90.0

    def test_normal_8(self):
        """Test: Test with typical usage scenario including both bulk and premium discounts."""
        result = calculate_discount(**{'price': 50, 'quantity': 20, 'is_premium': True})
        assert pytest.approx(result, rel=1e-2) == 76.5

    @given(
        price=st.floats(allow_nan=False, allow_infinity=False),
        quantity=st.integers(),
        is_premium=st.booleans(),
    )
    def test_properties(self, price, quantity, is_premium):
        result = calculate_discount(price, quantity, is_premium)
        assert isinstance(result, float)
