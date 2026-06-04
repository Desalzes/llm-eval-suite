from lib.geometry import area, Rectangle


def test_legacy_area_function_preserved():
    # Existing public API must keep working for current callers.
    assert area(3, 4) == 12
    assert area(0, 9) == 0


def test_rectangle_area():
    assert Rectangle(3, 4).area() == 12


def test_rectangle_attributes():
    r = Rectangle(2, 5)
    assert r.width == 2
    assert r.height == 5
