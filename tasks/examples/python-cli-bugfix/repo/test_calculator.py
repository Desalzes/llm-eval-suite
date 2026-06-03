import unittest

from calculator import add, multiply, subtract


class CalculatorTests(unittest.TestCase):
    def test_adds_two_numbers(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_multiplies_two_numbers(self) -> None:
        self.assertEqual(multiply(4, 3), 12)

    def test_subtracts_right_number_from_left_number(self) -> None:
        self.assertEqual(subtract(7, 2), 5)


if __name__ == "__main__":
    unittest.main()
