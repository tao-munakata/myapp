"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const processFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith("image/")) {
        setError("画像ファイルを選択してください");
        return;
      }
      setLoading(true);
      setError(null);

      const form = new FormData();
      form.append("file", file);

      try {
        const res = await fetch("/api/process", { method: "POST", body: form });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail ?? "処理に失敗しました");
        }
        const data = await res.json();
        // エディターにデータを渡す（sessionStorage 経由）
        sessionStorage.setItem("manualine_result", JSON.stringify(data));
        router.push("/editor");
      } catch (e) {
        setError(e instanceof Error ? e.message : "エラーが発生しました");
        setLoading(false);
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <span className="text-2xl font-black text-blue-600 tracking-tight">
            Manualine
          </span>
          <span className="text-slate-400 text-sm">
            写真 → 線画マニュアル、30秒で完成
          </span>
        </div>
      </header>

      {/* ヒーロー */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-16 gap-10">
        <div className="text-center max-w-xl">
          <h1 className="text-4xl font-black text-slate-900 leading-tight mb-4">
            写真を撮るだけで<br />
            <span className="text-blue-600">プロ品質のマニュアル</span>
          </h1>
          <p className="text-slate-500 text-lg">
            AIが構造を理解して線画に変換。矢印・番号を自動付与。
            新人でも迷わない手順書が、現場でその場で作れます。
          </p>
        </div>

        {/* アップロードエリア */}
        <div
          className={[
            "w-full max-w-lg border-2 border-dashed rounded-2xl",
            "flex flex-col items-center justify-center gap-4 py-16 px-8",
            "cursor-pointer transition-colors",
            dragging
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50",
          ].join(" ")}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          {loading ? (
            <>
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-blue-600 font-medium">AI処理中...</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-blue-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <div className="text-center">
                <p className="text-slate-700 font-semibold text-lg">
                  写真をドロップ、またはタップ
                </p>
                <p className="text-slate-400 text-sm mt-1">
                  JPG / PNG / WebP 対応・最大10MB
                </p>
              </div>
            </>
          )}
        </div>

        <input
          id="file-input"
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={onFileChange}
        />

        {error && (
          <p className="text-red-500 text-sm bg-red-50 px-4 py-2 rounded-lg">
            {error}
          </p>
        )}

        {/* 機能紹介 */}
        <div className="grid grid-cols-3 gap-4 max-w-lg w-full mt-4">
          {[
            { icon: "📸", label: "写真から線画", desc: "背景を除去して構造だけ抽出" },
            { icon: "🎯", label: "自動で矢印付け", desc: "ネジ・ボタンを自動検出" },
            { icon: "📤", label: "そのまま共有", desc: "PNG保存・リンク共有" },
          ].map((f) => (
            <div
              key={f.label}
              className="bg-white rounded-xl p-4 text-center border border-slate-100 shadow-sm"
            >
              <div className="text-2xl mb-2">{f.icon}</div>
              <p className="text-slate-800 font-semibold text-sm">{f.label}</p>
              <p className="text-slate-400 text-xs mt-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="text-center py-6 text-slate-400 text-xs">
        © 2026 Manualine — 現場のマニュアルを、もっとかんたんに
      </footer>
    </main>
  );
}
