import sys
import unittest
from unittest.mock import patch, MagicMock
from luma_core.ui import safe_input

class TestSafeInput(unittest.TestCase):
    @patch('luma_core.ui.os.isatty', return_value=True)
    @patch('luma_core.ui.sys.stdin')
    @patch('luma_core.ui.sys.stdout')
    @patch('luma_core.ui.tty.setcbreak')
    @patch('luma_core.ui.termios.tcgetattr')
    @patch('luma_core.ui.termios.tcsetattr')
    def test_safe_input_basic(self, mock_tcset, mock_tcget, mock_setcbreak, mock_stdout, mock_stdin, mock_isatty):
        # Simulate typing 'abc' then Enter (\n)
        mock_stdin.read.side_effect = ['a', 'b', 'c', '\n']
        mock_stdin.fileno.return_value = 0
        
        result = safe_input("Prompt: ")
        
        self.assertEqual(result, "abc")
        # Ensure prompt was printed
        mock_stdout.write.assert_any_call("Prompt: ")
        mock_stdout.flush.assert_called()

    @patch('luma_core.ui.os.isatty', return_value=True)
    @patch('luma_core.ui.sys.stdin')
    @patch('luma_core.ui.tty.setcbreak')
    @patch('luma_core.ui.termios.tcgetattr')
    @patch('luma_core.ui.termios.tcsetattr')
    def test_safe_input_carriage_return(self, mock_tcset, mock_tcget, mock_setcbreak, mock_stdin, mock_isatty):
        # Simulate typing 'ok' then Carriage Return (\r)
        mock_stdin.read.side_effect = ['o', 'k', '\r']
        mock_stdin.fileno.return_value = 0
        
        result = safe_input("Test: ")
        
        self.assertEqual(result, "ok")

    @patch('luma_core.ui.os.isatty', return_value=True)
    @patch('luma_core.ui.sys.stdin')
    @patch('luma_core.ui.tty.setcbreak')
    @patch('luma_core.ui.termios.tcgetattr')
    @patch('luma_core.ui.termios.tcsetattr')
    def test_safe_input_backspace(self, mock_tcset, mock_tcget, mock_setcbreak, mock_stdin, mock_isatty):
        # Simulate 'abc', then backspace (char 127), then 'd', then \n
        mock_stdin.read.side_effect = ['a', 'b', 'c', '\x7f', 'd', '\n']
        mock_stdin.fileno.return_value = 0
        
        result = safe_input("Type: ")
        
        # 'abc' + backspace -> 'ab' + 'd' -> 'abd'
        self.assertEqual(result, "abd")

if __name__ == '__main__':
    unittest.main()
