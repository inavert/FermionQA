import unittest 

class TestSimulation(unittest.TestCase):
    def example(self):
        test_example_a = 1
        test_example_b = 1
        self.assertEqual(test_example_a, test_example_b)

if __name__ == "__main__":
    unittest.main()