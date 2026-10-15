"""
Polar H10 データ解析スクリプト
使い方:
  python analyze.py                        # data/ 内の最新セッションを解析
  python analyze.py data/ecg_XXX.csv      # 指定ファイルを解析

出力:
  data/analysis_XXX/
    ecg_waveform.png     - ECG波形 + QRS検出
    hrv_rr.png           - RR間隔時系列 + HRV統計
    poincare.png         - ポアンカレプロット
    report.json          - 数値サマリー
"""
import sys
import json
import csv
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")  # ヘッドレス
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── 設定 ─────────────────────────────────────────────────────
FS = 130.0  # ECGサンプリング周波数 (Hz)

DATA_DIR = Path(__file__).parent / "data"

# ── データ読み込み ────────────────────────────────────────────
def find_latest_session(data_dir: Path):
    ecg_files = sorted(data_dir.glob("ecg_*.csv"))
    if not ecg_files:
        raise FileNotFoundError("data/ にECGファイルが見つかりません")
    return ecg_files[-1]

def load_ecg(ecg_path: Path):
    t, v = [], []
    with ecg_path.open() as f:
        for row in csv.DictReader(f):
            t.append(float(row["timestamp_sec"]))
            v.append(int(row["ecg_uv"]))
    return np.array(t), np.array(v, dtype=float)

def load_hr(hr_path: Path):
    elapsed, hr, rr = [], [], []
    with hr_path.open() as f:
        for row in csv.DictReader(f):
            elapsed.append(float(row["elapsed_sec"]))
            hr.append(int(row["hr_bpm"]))
            if row["rr_ms"] and row["rr_ms"] != "None":
                rr.append(float(row["rr_ms"]))
    return np.array(elapsed), np.array(hr), np.array(rr)

def load_meta(meta_path: Path):
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return {}

# ── ECG前処理 ─────────────────────────────────────────────────
def preprocess_ecg(ecg: np.ndarray, fs: float = FS):
    """
    バンドパスフィルタ (0.5 – 40 Hz) でベースラインドリフトと
    高周波ノイズを除去する
    """
    sos = signal.butter(4, [0.5, 40.0], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, ecg)

# ── Pan-Tompkins 簡易版 QRS 検出 ──────────────────────────────
def detect_qrs(ecg_filtered: np.ndarray, fs: float = FS):
    """
    Pan-Tompkins アルゴリズムの簡易実装
    Returns: R-peak の sample index 配列
    """
    # 微分
    diff = np.diff(ecg_filtered)
    # 二乗
    sq = diff ** 2
    # 移動積分 (150ms窓)
    win = int(0.150 * fs)
    mwi = np.convolve(sq, np.ones(win) / win, mode="same")

    # 閾値: 最大値の30%
    threshold = 0.30 * np.max(mwi)
    above = mwi > threshold

    # 連続区間の最大点を R ピークとする
    r_peaks = []
    in_peak = False
    start = 0
    refractory = int(0.20 * fs)  # 不応期 200ms

    for i, val in enumerate(above):
        if val and not in_peak:
            in_peak = True
            start = i
        elif not val and in_peak:
            in_peak = False
            seg = ecg_filtered[start:i]
            if len(seg) == 0:
                continue
            peak_idx = start + int(np.argmax(np.abs(seg)))
            if r_peaks and (peak_idx - r_peaks[-1]) < refractory:
                # 不応期内はより大きい方を採用
                if abs(ecg_filtered[peak_idx]) > abs(ecg_filtered[r_peaks[-1]]):
                    r_peaks[-1] = peak_idx
            else:
                r_peaks.append(peak_idx)

    return np.array(r_peaks)

# ── HRV 計算 ─────────────────────────────────────────────────
def calc_hrv(rr_ms: np.ndarray):
    """標準的なtime-domain HRV指標"""
    if len(rr_ms) < 3:
        return {}
    diff = np.diff(rr_ms)
    rmssd = float(np.sqrt(np.mean(diff ** 2)))
    sdnn  = float(np.std(rr_ms, ddof=1))
    nn50  = int(np.sum(np.abs(diff) > 50))
    pnn50 = float(nn50 / len(diff) * 100)
    mean_rr = float(np.mean(rr_ms))
    mean_hr = float(60000.0 / mean_rr)
    return {
        "mean_rr_ms": round(mean_rr, 2),
        "mean_hr_bpm": round(mean_hr, 1),
        "sdnn_ms": round(sdnn, 2),
        "rmssd_ms": round(rmssd, 2),
        "nn50": nn50,
        "pnn50_pct": round(pnn50, 1),
        "min_rr_ms": round(float(np.min(rr_ms)), 2),
        "max_rr_ms": round(float(np.max(rr_ms)), 2),
    }

# ── プロット ─────────────────────────────────────────────────
def plot_ecg(t, ecg_raw, ecg_filt, r_peaks, out_path: Path):
    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    fig.suptitle("ECG Waveform — Polar H10", fontsize=14)

    # 上段: 生波形
    axes[0].plot(t, ecg_raw, color="#aaaaaa", linewidth=0.5, label="Raw")
    axes[0].set_ylabel("ECG (μV)")
    axes[0].set_title("Raw ECG")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    # 下段: フィルタ済 + Rピーク
    axes[1].plot(t, ecg_filt, color="#1f77b4", linewidth=0.8, label="Filtered (0.5–40 Hz)")
    if len(r_peaks):
        axes[1].scatter(t[r_peaks], ecg_filt[r_peaks],
                        color="red", s=30, zorder=5, label=f"R-peaks ({len(r_peaks)})")
    axes[1].set_ylabel("ECG (μV)")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_title("Filtered ECG + R-peak Detection")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  保存: {out_path}")


def plot_hrv(elapsed, hr, rr_from_ecg_ms, rr_from_hr_ms, hrv_stats, out_path: Path):
    fig = plt.figure(figsize=(14, 9))
    fig.suptitle("Heart Rate & HRV — Polar H10", fontsize=14)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    ax_hr  = fig.add_subplot(gs[0, :])
    ax_rr  = fig.add_subplot(gs[1, 0])
    ax_txt = fig.add_subplot(gs[1, 1])

    # 上段: HR時系列
    ax_hr.plot(elapsed, hr, "o-", color="#e74c3c", markersize=3, linewidth=1)
    ax_hr.set_xlabel("Time (s)")
    ax_hr.set_ylabel("Heart Rate (bpm)")
    ax_hr.set_title("Heart Rate over Time (GATT HR Measurement)")
    ax_hr.grid(True, alpha=0.3)

    # 下段左: RR 時系列
    if len(rr_from_hr_ms):
        ax_rr.plot(rr_from_hr_ms, ".-", color="#3498db", markersize=4, linewidth=0.8, label="from GATT HR")
    if len(rr_from_ecg_ms):
        ax_rr.plot(rr_from_ecg_ms, ".-", color="#e67e22", markersize=3, linewidth=0.8, alpha=0.7, label="from ECG R-peaks")
    ax_rr.set_xlabel("Beat #")
    ax_rr.set_ylabel("RR interval (ms)")
    ax_rr.set_title("RR Intervals")
    ax_rr.legend()
    ax_rr.grid(True, alpha=0.3)

    # 下段右: HRV 統計テキスト
    ax_txt.axis("off")
    if hrv_stats:
        lines = [
            "HRV Statistics (GATT RR)",
            "─" * 28,
            f"Mean HR:  {hrv_stats.get('mean_hr_bpm','N/A'):>7} bpm",
            f"Mean RR:  {hrv_stats.get('mean_rr_ms','N/A'):>7} ms",
            f"SDNN:     {hrv_stats.get('sdnn_ms','N/A'):>7} ms",
            f"RMSSD:    {hrv_stats.get('rmssd_ms','N/A'):>7} ms",
            f"NN50:     {hrv_stats.get('nn50','N/A'):>7}",
            f"pNN50:    {hrv_stats.get('pnn50_pct','N/A'):>7} %",
            f"Min RR:   {hrv_stats.get('min_rr_ms','N/A'):>7} ms",
            f"Max RR:   {hrv_stats.get('max_rr_ms','N/A'):>7} ms",
        ]
        ax_txt.text(0.05, 0.95, "\n".join(lines),
                    transform=ax_txt.transAxes,
                    fontfamily="monospace", fontsize=11,
                    verticalalignment="top")

    plt.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  保存: {out_path}")


def plot_poincare(rr_ms: np.ndarray, out_path: Path):
    if len(rr_ms) < 4:
        return
    rr_n  = rr_ms[:-1]
    rr_n1 = rr_ms[1:]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(rr_n, rr_n1, alpha=0.6, s=20, color="#2ecc71")
    ax.set_xlabel("RR(n) (ms)")
    ax.set_ylabel("RR(n+1) (ms)")
    ax.set_title("Poincaré Plot — RR Interval Dynamics")
    ax.set_aspect("equal")

    # 45度対角線
    lim_min = min(rr_n.min(), rr_n1.min()) - 20
    lim_max = max(rr_n.max(), rr_n1.max()) + 20
    ax.plot([lim_min, lim_max], [lim_min, lim_max],
            "k--", linewidth=0.8, alpha=0.4, label="Identity line")

    # SD1/SD2 楕円
    sd1 = float(np.std(rr_n1 - rr_n, ddof=1) / np.sqrt(2))
    sd2 = float(np.std(rr_n1 + rr_n, ddof=1) / np.sqrt(2))
    cx  = float(np.mean(rr_n))
    cy  = float(np.mean(rr_n1))

    theta = np.linspace(0, 2 * np.pi, 200)
    # 45度回転した楕円
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    x = cx + sd2 * cos_t * np.cos(np.pi/4) - sd1 * sin_t * np.sin(np.pi/4)
    y = cy + sd2 * cos_t * np.sin(np.pi/4) + sd1 * sin_t * np.cos(np.pi/4)
    ax.plot(x, y, "r-", linewidth=1.5, alpha=0.8, label=f"SD1={sd1:.1f}ms SD2={sd2:.1f}ms")

    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  保存: {out_path}")


# ── メイン ───────────────────────────────────────────────────
def main():
    # ファイル選択
    if len(sys.argv) > 1:
        ecg_path = Path(sys.argv[1])
    else:
        ecg_path = find_latest_session(DATA_DIR)

    stem = ecg_path.stem.replace("ecg_", "")
    hr_path   = ecg_path.parent / f"hr_{stem}.csv"
    meta_path = ecg_path.parent / f"meta_{stem}.csv"
    meta_path_json = ecg_path.parent / f"meta_{stem}.json"

    out_dir = DATA_DIR / f"analysis_{stem}"
    out_dir.mkdir(exist_ok=True)

    print(f"解析対象: {ecg_path.name}")
    print(f"出力先  : {out_dir}/")

    # データ読み込み
    meta = load_meta(meta_path_json)
    t, ecg_raw = load_ecg(ecg_path)
    print(f"ECG: {len(ecg_raw)} samples  ({len(ecg_raw)/FS:.1f} s)")

    # t をセッション開始から相対時刻に
    t_rel = t - t[0]

    # HR / RR (GATT)
    rr_from_hr = np.array([])
    hr_elapsed = np.array([])
    hr_vals    = np.array([])
    if hr_path.exists():
        hr_elapsed, hr_vals, rr_from_hr = load_hr(hr_path)
        print(f"HR : {len(hr_vals)} records,  RR: {len(rr_from_hr)} intervals")

    # ECG前処理
    print("ECG前処理中...")
    ecg_filt = preprocess_ecg(ecg_raw)

    # QRS検出
    print("QRS検出中...")
    r_peaks = detect_qrs(ecg_filt)
    print(f"  R-peaks検出: {len(r_peaks)} 個")

    # ECGから直接RR計算
    rr_from_ecg = np.array([])
    if len(r_peaks) >= 2:
        rr_from_ecg = np.diff(r_peaks) / FS * 1000  # ms

    # HRV統計 (GAT RRを優先、なければECGRRを使用)
    rr_for_hrv = rr_from_hr if len(rr_from_hr) >= 3 else rr_from_ecg
    hrv_stats = calc_hrv(rr_for_hrv)
    print(f"HRV: {hrv_stats}")

    # プロット
    print("プロット生成中...")
    plot_ecg(t_rel, ecg_raw, ecg_filt, r_peaks, out_dir / "ecg_waveform.png")
    plot_hrv(hr_elapsed - hr_elapsed[0] if len(hr_elapsed) else hr_elapsed,
             hr_vals, rr_from_ecg, rr_from_hr, hrv_stats,
             out_dir / "hrv_rr.png")
    plot_poincare(rr_for_hrv, out_dir / "poincare.png")

    # レポート JSON
    report = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "source_ecg": str(ecg_path),
        "source_hr": str(hr_path) if hr_path.exists() else None,
        "ecg_samples": int(len(ecg_raw)),
        "ecg_duration_sec": round(float(len(ecg_raw) / FS), 2),
        "r_peaks_detected": int(len(r_peaks)),
        "ecg_rr_intervals": int(len(rr_from_ecg)),
        "gatt_rr_intervals": int(len(rr_from_hr)),
        "hrv": hrv_stats,
        "device_info": meta.get("device_info", {}),
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"  保存: {report_path}")

    print(f"\n完了: {out_dir}/")


if __name__ == "__main__":
    main()
