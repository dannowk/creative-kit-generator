"""Font resolution must behave the same on macOS and Windows."""

import os
import tempfile
import unittest

from kit import brand


class FindFont(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.font = os.path.join(self.dir, "Brand-Bold.otf")
        with open(self.font, "wb") as f:
            f.write(b"not a real font, only a name to resolve")

    def test_windows_separators_resolve_on_posix(self):
        self.assertEqual(brand.find_font("sub\\Brand-Bold.otf", [self.dir]), self.font)

    def test_subfolder_prefix_absent_here_falls_back_to_basename(self):
        self.assertEqual(brand.find_font("fonts/Brand-Bold.otf", [self.dir]), self.font)

    def test_stem_match_is_case_insensitive(self):
        found = brand.find_font("brand-bold.otf", [self.dir])
        self.assertTrue(found and os.path.samefile(found, self.font))

    def test_absolute_path_passes_through(self):
        self.assertEqual(brand.find_font(self.font, []), self.font)

    def test_empty_and_unknown(self):
        self.assertIsNone(brand.find_font("", [self.dir]))
        self.assertIsNone(brand.find_font("nope.otf", [self.dir]))


class FontDirs(unittest.TestCase):
    def test_mac_user_allusers_and_system_dirs_are_searched(self):
        dirs = brand.font_dirs()
        for d in (os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
                  "/System/Library/Fonts", "/System/Library/Fonts/Supplemental"):
            self.assertIn(d, dirs)

    def test_windows_user_and_system_dirs_are_searched(self):
        dirs = [d.replace("\\", "/") for d in brand.font_dirs()]
        self.assertTrue(any(d.endswith("Microsoft/Windows/Fonts") for d in dirs))
        self.assertTrue(any(d.endswith("Windows/Fonts") for d in dirs))

    def test_brand_dirs_come_before_system_dirs(self):
        dirs = brand.font_dirs(["/brand/fonts"])
        self.assertLess(dirs.index("/brand/fonts"), dirs.index("/Library/Fonts"))


class FontBookFallback(unittest.TestCase):
    def test_missing_brand_font_substitutes_an_os_fallback(self):
        book = brand.FontBook({"display": {"file": "absent.otf"}}, [])
        candidates = [c for c in brand.FALLBACK["display"] if os.path.isfile(c)]
        if not candidates:
            with self.assertRaises(FileNotFoundError):
                book.spec("display")
            return
        path, _ = book.spec("display")
        self.assertEqual(path, candidates[0])
        self.assertEqual(book.missing, ["absent.otf"])
        self.assertEqual(book.substituted, [("display", os.path.basename(candidates[0]))])


if __name__ == "__main__":
    unittest.main()