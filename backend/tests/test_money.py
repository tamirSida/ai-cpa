from app.utils.money import round_ils, format_ils

def test_round_ils_half_up():
    assert round_ils(10.005) == 10.01
    assert round_ils(2800) == 2800.0
    assert round_ils(99.994) == 99.99

def test_format_ils():
    assert format_ils(2800) == "₪2,800"
    assert format_ils(99.5) == "₪99.50"
    assert format_ils(1234567.89) == "₪1,234,567.89"
