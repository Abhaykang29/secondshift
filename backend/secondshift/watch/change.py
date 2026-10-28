"""Background / change detection (spec section 9.14).

Running-average background; change = fraction of pixels whose difference
exceeds CHANGE_PIXEL_DIFF. The gate consults this before any model call.
Depends on: numpy, opencv.
"""

import cv2
import numpy as np


class ChangeDetector:
    """Running-average change detector over grayscale frames."""

    def __init__(self, pixel_diff: float = 25.0, alpha: float = 0.05) -> None:
        self.pixel_diff = pixel_diff
        self.alpha = alpha
        self._background: np.ndarray | None = None

    def change_fraction(self, frame: np.ndarray) -> float:
        """Fraction of changed pixels vs the background; updates the model."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        gray_f = gray.astype(np.float32)
        if self._background is None:
            self._background = gray_f
            return 0.0
        diff = cv2.absdiff(gray, cv2.convertScaleAbs(self._background))
        fraction = float((diff > self.pixel_diff).mean())
        self._background = (1 - self.alpha) * self._background + self.alpha * gray_f
        return fraction
