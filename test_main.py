import unittest
import subprocess

class TestMain(unittest.TestCase):

    def test_main_execution(self):

        try:
            process = subprocess.run(['python', 'main.py'], capture_output=True, text=True, check=True)
            self.assertEqual(process.stdout.strip(), 'Hello, world!')
        except subprocess.CalledProcessError as e:
            self.fail(f"Subprocess failed with error: {e}")


if __name__ == '__main__':
    unittest.main()
