"""Frame quality metrics (spec section 9.1 step 3).

sharpness = variance of the Laplacian (grayscale); brightness = mean luma.
A frame is usable only inside the configured thresholds - unusable frames
become CannotAssess reasons downstream, never silent drops.
Depends on: opencv, numpy.
"""

import cv2
import numpy as np


def frame_metrics(image: np.ndarray) -> tuple[float, float]:
    """Return (sharpness, brightness) for one BGR frame array."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    return sharpness, brightness


def is_usable(
    sharpness: float,
    brightness: float,
    sharpness_min: float,
    brightness_min: float,
    brightness_max: float,
) -> bool:
    """Whether a frame passes the configured quality thresholds."""
    return sharpness >= sharpness_min and brightness_min <= brightness <= brightness_max


def metrics_for_file(path: str) -> tuple[float, float]:
    """Load an image file and return its (sharpness, brightness)."""
    image = cv2.imread(path)
    if image is None:
        return 0.0, 0.0
    return frame_metrics(image)
