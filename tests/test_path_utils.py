import unittest

from src.path_utils import normalize_config_path


class PathUtilsTests(unittest.TestCase):
    def test_normalize_config_path_accepts_terminal_escaped_icloud_path(self):
        path = "/Users/yourname/Library/Mobile\\ Documents/com\\~apple\\~CloudDocs/researchspace "

        self.assertEqual(
            normalize_config_path(path),
            "/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/researchspace",
        )

    def test_normalize_config_path_preserves_plain_path_with_spaces(self):
        path = "/Users/yourname/Library/Mobile Documents/com~apple~CloudDocs/researchspace"

        self.assertEqual(normalize_config_path(path), path)


if __name__ == "__main__":
    unittest.main()
