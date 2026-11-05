import cv2
import numpy as np
from dataclasses import dataclass


@dataclass
class DetectedPoint:
    x: int
    y: int
    radius: int
    confidence: float


def process_image(file_bytes: bytes) -> tuple[bytes, list[DetectedPoint]]:
    """
    画像を線画に変換し、操作点（ネジ・ボタン）を検出する。
    Returns: (png_bytes, detected_points)
    """
    npimg = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("画像の読み込みに失敗しました")

    h, w = img.shape[:2]

    # ── 線画変換 ────────────────────────────────────────────────
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ノイズ除去しながらエッジを保持
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # 適応的エッジ検出（画像の明るさに依存しない）
    edges = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=9, C=2
    )

    # Canny で細部エッジを補完
    canny = cv2.Canny(denoised, 40, 120)
    combined = cv2.bitwise_and(edges, cv2.bitwise_not(canny))

    # 線をわずかに太くして見やすくする
    kernel = np.ones((2, 2), np.uint8)
    line_art = cv2.erode(combined, kernel, iterations=1)

    # RGB に変換（白背景・黒線）
    output = cv2.cvtColor(line_art, cv2.COLOR_GRAY2BGR)

    # ── 操作点検出（円形 = ネジ・ボタン・ノブ）──────────────────
    points: list[DetectedPoint] = []

    circles = cv2.HoughCircles(
        denoised,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(30, min(w, h) // 15),
        param1=60,
        param2=28,
        minRadius=max(5, min(w, h) // 60),
        maxRadius=max(40, min(w, h) // 8),
    )

    if circles is not None:
        circles_int = np.uint16(np.around(circles[0]))
        # 信頼度順にソート（単純に中心からの距離で代替）
        cx, cy = w // 2, h // 2
        scored = sorted(
            circles_int,
            key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2)
        )
        for i, (x, y, r) in enumerate(scored[:5]):  # 最大5点
            confidence = 1.0 - (i * 0.15)
            points.append(DetectedPoint(int(x), int(y), int(r), confidence))

    _, buffer = cv2.imencode(".png", output)
    return buffer.tobytes(), points
