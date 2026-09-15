import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLLERS = os.path.join(PROJECT_ROOT, "controllers")
if CONTROLLERS not in sys.path:
    sys.path.insert(0, CONTROLLERS)

from Utils.BallPerception import CameraBallDetector


class CameraBallDetectorTests(unittest.TestCase):
    def test_detects_compact_orange_blob(self):
        def pixel_at(x, y):
            if 42 <= x <= 50 and 30 <= y <= 38:
                return (230, 100, 8)
            return (20, 120, 30)

        result = CameraBallDetector.analyse_pixels(100, 80, pixel_at, stride=1)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["u"], 46.0)
        self.assertAlmostEqual(result["v"], 34.0)
        self.assertGreater(result["radius_px"], 4.0)

    def test_rejects_non_orange_background(self):
        result = CameraBallDetector.analyse_pixels(
            60, 40, lambda _x, _y: (25, 130, 35), stride=2
        )
        self.assertIsNone(result)

    def test_projects_bearing_range_to_world_xy(self):
        detection = {"bearing_rad": 0.0, "distance_m": 2.0}
        estimate = CameraBallDetector.estimate_world_xy(detection, [1.0, -0.5, 0.3], 0.0)
        self.assertEqual(estimate, [3.0, -0.5])


if __name__ == "__main__":
    unittest.main()
