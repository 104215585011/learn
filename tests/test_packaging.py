import unittest
from pathlib import Path

import build_exe


class PackagingTests(unittest.TestCase):
    def test_build_command_targets_windowless_launcher(self):
        command = build_exe.build_command()

        self.assertIn("--windowed", command)
        self.assertEqual(Path(command[-1]).name, "launch.pyw")


if __name__ == "__main__":
    unittest.main()
