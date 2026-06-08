import os
import tempfile
import unittest

from src.markdown_parser import MarkdownParser


class MarkdownParserTests(unittest.TestCase):
    def test_get_markdown_files_includes_stable_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = os.path.join(tmpdir, "notes")
            os.makedirs(folder)
            md_path = os.path.join(folder, "daily.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# Daily\n")

            files = MarkdownParser(tmpdir).get_markdown_files()

            self.assertEqual(files[0]["relative_path"], os.path.join("notes", "daily.md"))


if __name__ == "__main__":
    unittest.main()
