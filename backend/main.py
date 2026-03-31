import base64
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from image_proc import process_image, DetectedPoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Manualine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番では manualine.tech に絞る
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class Point(BaseModel):
    x: int
    y: int
    radius: int
    confidence: float


class ProcessResponse(BaseModel):
    image_base64: str
    detected_points: list[Point]
    width: int
    height: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/process", response_model=ProcessResponse)
async def process(file: UploadFile = File(...)) -> ProcessResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="画像ファイルを送信してください")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB 上限
        raise HTTPException(status_code=413, detail="ファイルサイズは10MB以下にしてください")

    logger.info(f"Processing image: {file.filename} ({len(content)} bytes)")

    try:
        png_bytes, points = process_image(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Image processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="画像処理に失敗しました")

    # 幅・高さを取得
    import cv2
    import numpy as np
    arr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]

    return ProcessResponse(
        image_base64=base64.b64encode(png_bytes).decode(),
        detected_points=[
            Point(x=p.x, y=p.y, radius=p.radius, confidence=p.confidence)
            for p in points
        ],
        width=w,
        height=h,
    )
