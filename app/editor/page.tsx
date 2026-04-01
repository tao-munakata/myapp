"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";

interface Point {
  x: number;
  y: number;
  radius: number;
  confidence: number;
}

interface Annotation {
  id: number;
  x: number;
  y: number;
  label: string;
  mode: "arrow" | "circle" | "text";
  description: string;
}

interface ProcessResult {
  image_base64: string;
  detected_points: Point[];
  width: number;
  height: number;
}

type ToolMode = "arrow" | "circle" | "text" | "move" | "delete";

export default function EditorPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [tool, setTool] = useState<ToolMode>("arrow");
  const [nextId, setNextId] = useState(1);
  const [dragging, setDragging] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);

  // データ読み込み
  useEffect(() => {
    const raw = sessionStorage.getItem("manualine_result");
    if (!raw) {
      router.replace("/");
      return;
    }
    const data: ProcessResult = JSON.parse(raw);
    setResult(data);

    // AI検出点を初期アノテーションとして追加
    const initial: Annotation[] = data.detected_points
      .slice(0, 3)
      .map((p, i) => ({
        id: i + 1,
        x: p.x,
        y: p.y,
        label: String(i + 1),
        mode: "circle",
        description: "",
      }));
    setAnnotations(initial);
    setNextId(initial.length + 1);
  }, [router]);

  // 画像読み込み & Canvas描画
  useEffect(() => {
    if (!result) return;
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      renderCanvas();
    };
    img.src = `data:image/png;base64,${result.image_base64}`;
  }, [result]);

  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const maxW = Math.min(window.innerWidth - 32, 800);
    const s = Math.min(1, maxW / img.naturalWidth);
    setScale(s);
    canvas.width = img.naturalWidth * s;
    canvas.height = img.naturalHeight * s;

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    // アノテーション描画
    annotations.forEach((a) => {
      const ax = a.x * s;
      const ay = a.y * s;
      ctx.save();

      if (a.mode === "arrow") {
        drawArrow(ctx, ax + 50, ay + 50, ax, ay);
      }

      // 番号バッジ
      const r = 14;
      ctx.fillStyle = "#2563EB";
      ctx.beginPath();
      ctx.arc(ax, ay, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.font = `bold ${r}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(a.label, ax, ay);

      ctx.restore();
    });
  }, [annotations, scale]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  function drawArrow(
    ctx: CanvasRenderingContext2D,
    fromX: number,
    fromY: number,
    toX: number,
    toY: number
  ) {
    const angle = Math.atan2(toY - fromY, toX - fromX);
    const len = Math.sqrt((toX - fromX) ** 2 + (toY - fromY) ** 2);
    if (len < 10) return;

    ctx.strokeStyle = "#EF4444";
    ctx.fillStyle = "#EF4444";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(fromX, fromY);
    ctx.lineTo(toX, toY);
    ctx.stroke();

    // 矢印の先
    const hw = 10;
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(
      toX - hw * Math.cos(angle - Math.PI / 6),
      toY - hw * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      toX - hw * Math.cos(angle + Math.PI / 6),
      toY - hw * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fill();
  }

  function getCanvasPos(e: React.MouseEvent | React.TouchEvent): { x: number; y: number } {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) / scale,
      y: (clientY - rect.top) / scale,
    };
  }

  function findNearAnnotation(x: number, y: number): number | null {
    for (const a of annotations) {
      const d = Math.sqrt((a.x - x) ** 2 + (a.y - y) ** 2);
      if (d < 20) return a.id;
    }
    return null;
  }

  function onCanvasMouseDown(e: React.MouseEvent) {
    const pos = getCanvasPos(e);

    if (tool === "move") {
      const found = findNearAnnotation(pos.x, pos.y);
      if (found !== null) {
        const a = annotations.find((a) => a.id === found)!;
        setDragging(found);
        setDragOffset({ x: pos.x - a.x, y: pos.y - a.y });
      }
      return;
    }

    if (tool === "delete") {
      const found = findNearAnnotation(pos.x, pos.y);
      if (found !== null) {
        setAnnotations((prev) => prev.filter((a) => a.id !== found));
      }
      return;
    }

    // 追加
    const newAnnotation: Annotation = {
      id: nextId,
      x: pos.x,
      y: pos.y,
      label: String(nextId),
      mode: tool === "text" ? "text" : tool,
      description: "",
    };
    setAnnotations((prev) => [...prev, newAnnotation]);
    setNextId((n) => n + 1);
  }

  function onCanvasMouseMove(e: React.MouseEvent) {
    if (dragging === null) return;
    const pos = getCanvasPos(e);
    setAnnotations((prev) =>
      prev.map((a) =>
        a.id === dragging
          ? { ...a, x: pos.x - dragOffset.x, y: pos.y - dragOffset.y }
          : a
      )
    );
  }

  function onCanvasMouseUp() {
    setDragging(null);
  }

  function downloadPNG() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `manualine-${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function resetAll() {
    setAnnotations([]);
    setNextId(1);
  }

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const tools: { id: ToolMode; label: string; icon: string }[] = [
    { id: "arrow", label: "矢印", icon: "→" },
    { id: "circle", label: "マーク", icon: "●" },
    { id: "move", label: "移動", icon: "✥" },
    { id: "delete", label: "削除", icon: "✕" },
  ];

  return (
    <main className="min-h-screen bg-slate-100 flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/")}
          className="text-slate-400 hover:text-slate-700 text-sm"
        >
          ← 戻る
        </button>
        <span className="font-black text-blue-600 text-lg">Manualine</span>
        <span className="flex-1" />
        <button
          onClick={resetAll}
          className="text-sm text-slate-500 hover:text-red-500 px-3 py-1 rounded"
        >
          リセット
        </button>
        <button
          onClick={downloadPNG}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          PNG 保存
        </button>
      </header>

      {/* ツールバー */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex gap-2 overflow-x-auto">
        {tools.map((t) => (
          <button
            key={t.id}
            onClick={() => setTool(t.id)}
            className={[
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
              tool === t.id
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200",
            ].join(" ")}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
        <span className="ml-auto text-slate-400 text-xs self-center">
          タップで追加 / ✥で移動
        </span>
      </div>

      {/* キャンバス */}
      <div className="flex-1 flex items-start justify-center p-4 overflow-auto">
        <canvas
          ref={canvasRef}
          className="rounded-xl shadow-lg cursor-crosshair max-w-full"
          onMouseDown={onCanvasMouseDown}
          onMouseMove={onCanvasMouseMove}
          onMouseUp={onCanvasMouseUp}
          onMouseLeave={onCanvasMouseUp}
        />
      </div>

      {/* アノテーション一覧 */}
      {annotations.length > 0 && (
        <div className="bg-white border-t border-slate-200 px-4 py-3">
          <p className="text-xs text-slate-500 mb-2 font-semibold">手順リスト</p>
          <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
            {annotations.map((a) => (
              <div key={a.id} className="flex items-center gap-2 text-sm">
                <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                  {a.label}
                </span>
                <input
                  type="text"
                  value={a.description}
                  onChange={(e) =>
                    setAnnotations((prev) =>
                      prev.map((ann) =>
                        ann.id === a.id
                          ? { ...ann, description: e.target.value }
                          : ann
                      )
                    )
                  }
                  placeholder={`手順 ${a.label} の説明を入力`}
                  className="flex-1 border border-slate-200 rounded px-2 py-1 text-sm text-slate-700 focus:outline-none focus:border-blue-400"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
