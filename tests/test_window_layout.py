import unittest

from window_layout import fit_window


class WindowLayoutTests(unittest.TestCase):
    def test_laptop_and_high_dpi_windows_fit_and_center_with_decorations(self):
        for area, scale in [((0, 0, 1366, 728), 1), ((0, 0, 1920, 1040), 1.25),
                            ((0, 0, 1366, 728), 1.5), ((0, 48, 1920, 1080), 1.5),
                            ((60, 0, 1920, 1080), 1), ((0, 0, 3840, 2080), 2)]:
            with self.subTest(area=area, scale=scale):
                frame = round(20 * scale), round(44 * scale)
                plan = fit_window(area, scale, frame)
                outer_width = round(plan.width * scale) + frame[0]
                outer_height = round(plan.height * scale) + frame[1]
                self.assertGreaterEqual(plan.x, area[0])
                self.assertGreaterEqual(plan.y, area[1])
                self.assertLessEqual(plan.x + outer_width, area[2])
                self.assertLessEqual(plan.y + outer_height, area[3])
                self.assertLessEqual(abs((2 * plan.x + outer_width) - (area[0] + area[2])), 1)
                self.assertLessEqual(abs((2 * plan.y + outer_height) - (area[1] + area[3])), 1)

    def test_small_laptop_uses_scrollable_layout(self):
        self.assertTrue(fit_window((0, 0, 1366, 728)).compact)
        self.assertTrue(fit_window((0, 0, 1920, 1040), 1.5).compact)

    def test_large_screen_keeps_readable_window_size(self):
        plan = fit_window((0, 0, 3840, 2080))
        self.assertEqual((plan.width, plan.height), (1180, 820))
        self.assertFalse(plan.compact)
