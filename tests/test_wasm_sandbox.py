import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wasm_sandbox import WasmSandbox

class TestWasmSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = WasmSandbox()

    def test_safe_code_execution(self):
        code = "print('Hello, secure world!')\nx = sum([1, 2, 3])\nprint(x)"
        result = self.sandbox.run_python_code(code)
        self.assertTrue(result["success"])
        self.assertIn("Hello, secure world!", result["output"])
        self.assertIn("6", result["output"])
        self.assertEqual(result["error"], "")

    def test_malicious_os_import_blocked(self):
        code = "import os\nos.system('echo Hacked')"
        result = self.sandbox.run_python_code(code)
        self.assertFalse(result["success"])
        self.assertIn("strictly forbidden", result["error"])

    def test_malicious_sys_import_blocked(self):
        code = "import sys\nprint(sys.path)"
        result = self.sandbox.run_python_code(code)
        self.assertFalse(result["success"])
        self.assertIn("strictly forbidden", result["error"])

if __name__ == '__main__':
    unittest.main()
