"""Camera-only football detection for the NAO controllers.

The detector deliberately consumes only camera pixels.  Supervisor ball truth
can be retained separately by the evaluation logger, but is never used by this
module or by a controller running with ``ROBOCUP_BALL_SOURCE=camera``.
"""

import math


class CameraBallDetector:
    """Detect the high-contrast orange training ball and estimate its pose.

    The supplied world uses a small orange football so that the initial
    perception baseline is inspectable and reproducible without downloading a
    model.  This is a colour-segmentation baseline, not a learned detector.
    """

    BALL_RADIUS_M = 0.068

    def __init__(self, camera, stride=2, min_samples=5):
        self.camera = camera
        self.stride = stride
        self.min_samples = min_samples

    @staticmethod
    def is_ball_pixel(red, green, blue):
        """Conservative orange threshold robust to Webots lighting changes."""
        return red >= 130 and green >= 45 and green <= 210 and blue <= 105 and red >= green * 1.25

    @classmethod
    def analyse_pixels(cls, width, height, pixel_at, stride=2, min_samples=5):
        """Return centroid/bounding-box statistics or ``None``.

        ``pixel_at(x, y)`` returns (red, green, blue).  Keeping this pure makes
        the segmentation testable without Webots or a live camera.
        """
        samples = []
        for y in range(0, height, stride):
            for x in range(0, width, stride):
                red, green, blue = pixel_at(x, y)
                if cls.is_ball_pixel(red, green, blue):
                    samples.append((x, y))

        if len(samples) < min_samples:
            return None

        xs = [sample[0] for sample in samples]
        ys = [sample[1] for sample in samples]
        width_px = max(xs) - min(xs) + stride
        height_px = max(ys) - min(ys) + stride
        aspect = min(width_px, height_px) / max(width_px, height_px)
        if aspect < 0.45:
            return None

        return {
            "u": sum(xs) / len(xs),
            "v": sum(ys) / len(ys),
            "samples": len(samples),
            "radius_px": max(1.0, math.sqrt(len(samples) * stride * stride / math.pi)),
            "aspect": aspect,
        }

    def detect(self):
        image = self.camera.getImage()
        if image is None:
            return None
        width = self.camera.getWidth()
        height = self.camera.getHeight()

        def pixel_at(x, y):
            return (
                self.camera.imageGetRed(image, width, x, y),
                self.camera.imageGetGreen(image, width, x, y),
                self.camera.imageGetBlue(image, width, x, y),
            )

        blob = self.analyse_pixels(width, height, pixel_at, self.stride, self.min_samples)
        if blob is None:
            return None

        focal_px = width / (2.0 * math.tan(self.camera.getFov() / 2.0))
        bearing = math.atan2(blob["u"] - (width - 1) / 2.0, focal_px)
        distance = self.BALL_RADIUS_M * focal_px / blob["radius_px"]
        if distance < 0.10 or distance > 8.0:
            return None
        confidence = min(1.0, blob["samples"] / 30.0) * blob["aspect"]
        return {
            **blob,
            "bearing_rad": bearing,
            "distance_m": distance,
            "confidence": confidence,
            "camera": self.camera.getName(),
        }

    @staticmethod
    def estimate_world_xy(detection, robot_xyz, yaw):
        """Project a bearing/range observation into the GPS/IMU world frame."""
        heading = yaw + detection["bearing_rad"]
        return [
            robot_xyz[0] + detection["distance_m"] * math.cos(heading),
            robot_xyz[1] + detection["distance_m"] * math.sin(heading),
        ]
