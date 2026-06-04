from roman import roman


def test_basic_examples():
    assert roman(1) == "I"
    assert roman(4) == "IV"
    assert roman(9) == "IX"
    assert roman(14) == "XIV"
    assert roman(40) == "XL"
