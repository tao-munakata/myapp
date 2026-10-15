"""
Polar H10 データ収集スクリプト
- Heart Rate + RR intervals (GATT 0x2A37)
- 生ECGデータ (Polar PMD, 130Hz 14-bit)
- バッテリー・デバイス情報
保存先: ./data/
"""
import asyncio
import csv
import json
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

from bleak import BleakClient

# ── デバイス設定 ────────────────────────────────────────────
POLAR_H10_ADDR = "24:AC:AC:1F:BD:C9"
DURATION_SEC   = int(sys.argv[1]) if len(sys.argv) > 1 else 60  # 収集秒数

# ── GATT UUID ────────────────────────────────────────────────
HR_MEAS_UUID   = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_UUID   = "00002a19-0000-1000-8000-00805f9b34fb"
BODY_LOC_UUID  = "00002a38-0000-1000-8000-00805f9b34fb"

DEVICE_INFO_UUIDS = {
    "manufacturer": "00002a29-0000-1000-8000-00805f9b34fb",
    "model":        "00002a24-0000-1000-8000-00805f9b34fb",
    "serial":       "00002a25-0000-1000-8000-00805f9b34fb",
    "hardware_rev": "00002a27-0000-1000-8000-00805f9b34fb",
    "firmware_rev": "00002a26-0000-1000-8000-00805f9b34fb",
    "software_rev": "00002a28-0000-1000-8000-00805f9b34fb",
}

# ── Polar PMD UUID ───────────────────────────────────────────
PMD_CP_UUID   = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"  # Control Point
PMD_DATA_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"  # Data stream

# ECG 開始コマンド: 130 Hz, 14-bit
ECG_START_CMD = bytearray([
    0x02,        # REQUEST_MEASUREMENT_START
    0x00,        # ECG
    0x00, 0x01, 0x82, 0x00,  # SAMPLE_RATE = 130 Hz
    0x01, 0x01, 0x0E, 0x00,  # RESOLUTION  = 14 bit
])
ECG_STOP_CMD = bytearray([0x03, 0x00])  # STOP ECG

# ── 出力設定 ─────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ts_str   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HR_FILE  = DATA_DIR / f"hr_{ts_str}.csv"
ECG_FILE = DATA_DIR / f"ecg_{ts_str}.csv"
META_FILE = DATA_DIR / f"meta_{ts_str}.json"


def parse_hr_measurement(data: bytearray) -> dict:
    """GATT Heart Rate Measurement (0x2A37) をパース"""
    flags = data[0]
    hr_format_16bit = flags & 0x01
    rr_present = (flags >> 4) & 0x01

    idx = 1
    if hr_format_16bit:
        hr_bpm = struct.unpack_from("<H", data, idx)[0]
        idx += 2
    else:
        hr_bpm = data[idx]
        idx += 1

    rr_intervals_ms = []
    if rr_present:
        while idx + 1 < len(data):
            rr_raw = struct.unpack_from("<H", data, idx)[0]
            rr_intervals_ms.append(round(rr_raw * 1000 / 1024, 2))
            idx += 2

    return {"hr_bpm": hr_bpm, "rr_ms": rr_intervals_ms}


def parse_ecg_data(data: bytearray) -> list[int]:
    """
    Polar PMD ECG データをパース
    フォーマット:
      byte 0   : 測定タイプ (0x00 = ECG)
      bytes 1-8: タイムスタンプ (ns, uint64 LE) ※H10では常に0
      byte 9   : フレームタイプ (0x00)
      bytes 10+: ECGサンプル, 各3バイト (符号付き24-bit LE, 実効14-bit)
    単位: μV (マイクロボルト)
    """
    if len(data) < 10:
        return []
    meas_type  = data[0]
    frame_type = data[9]
    if meas_type != 0x00:
        return []  # ECG以外は無視

    samples = []
    i = 10
    while i + 2 < len(data):
        raw = int.from_bytes(data[i:i+3], "little", signed=True)
        samples.append(raw)
        i += 3
    return samples


async def collect():
    start_wall = time.time()
    session_meta = {
        "session_start": datetime.now(timezone.utc).isoformat(),
        "duration_sec": DURATION_SEC,
        "device_address": POLAR_H10_ADDR,
        "device_info": {},
    }

    ecg_sample_index = 0
    ecg_t0 = None  # 最初のECGパケット受信時刻
    ECG_SAMPLE_INTERVAL_SEC = 1 / 130

    hr_rows  = []
    ecg_rows = []

    print(f"スキャン中 ({POLAR_H10_ADDR})...")
    from bleak import BleakScanner
    device = await BleakScanner.find_device_by_address(POLAR_H10_ADDR, timeout=15.0)
    if device is None:
        print("ERROR: Polar H10 が見つかりません")
        return

    disconnected = asyncio.Event()
    def on_disconnect(client):
        print("\n[警告] デバイス切断を検出")
        disconnected.set()

    print(f"接続中: {POLAR_H10_ADDR}  ({DURATION_SEC}秒間収集)")
    await asyncio.sleep(2.0)  # デバイス復帰待ち
    async with BleakClient(device, timeout=40.0, disconnected_callback=on_disconnect) as client:
        print("接続成功")

        # ── デバイス情報読み取り ──────────────────────────
        for key, uuid in DEVICE_INFO_UUIDS.items():
            try:
                val = await client.read_gatt_char(uuid)
                session_meta["device_info"][key] = val.decode("utf-8", errors="replace").strip()
            except Exception:
                pass

        try:
            body_loc_raw = await client.read_gatt_char(BODY_LOC_UUID)
            loc_map = {0: "Other", 1: "Chest", 2: "Wrist", 3: "Finger",
                       4: "Hand", 5: "Ear Lobe", 6: "Foot"}
            session_meta["device_info"]["body_sensor_location"] = loc_map.get(body_loc_raw[0], "Unknown")
        except Exception:
            pass

        try:
            bat_raw = await client.read_gatt_char(BATTERY_UUID)
            session_meta["device_info"]["battery_percent"] = bat_raw[0]
        except Exception:
            pass

        print("デバイス情報:", json.dumps(session_meta["device_info"], ensure_ascii=False, indent=2))

        # ── HR 通知ハンドラ ───────────────────────────────
        def hr_handler(sender, data):
            t = time.time()
            elapsed = round(t - start_wall, 3)
            parsed = parse_hr_measurement(bytearray(data))
            for rr in parsed["rr_ms"] or [None]:
                hr_rows.append({
                    "elapsed_sec": elapsed,
                    "hr_bpm": parsed["hr_bpm"],
                    "rr_ms": rr,
                })
            rr_str = f"  RR={parsed['rr_ms']}ms" if parsed["rr_ms"] else ""
            print(f"  [HR] {elapsed:6.1f}s  {parsed['hr_bpm']} bpm{rr_str}")

        # ── ECG 通知ハンドラ ──────────────────────────────
        def ecg_handler(sender, data):
            nonlocal ecg_sample_index, ecg_t0
            t = time.time()
            if ecg_t0 is None:
                ecg_t0 = t
            samples = parse_ecg_data(bytearray(data))
            for s in samples:
                sample_t = ecg_t0 + ecg_sample_index * ECG_SAMPLE_INTERVAL_SEC
                ecg_rows.append({
                    "sample_index": ecg_sample_index,
                    "timestamp_sec": round(sample_t - start_wall, 6),
                    "ecg_uv": s,
                })
                ecg_sample_index += 1
            if samples:
                print(f"  [ECG] +{ecg_sample_index} samples  last={samples[-1]} μV")

        # ── サブスクライブ開始 ────────────────────────────
        # ECG データ通知を先にサブスクライブ (開始コマンド前)
        await client.start_notify(PMD_DATA_UUID, ecg_handler)
        await client.start_notify(HR_MEAS_UUID, hr_handler)

        # PMD Control Point の通知を有効化してからECG開始コマンドを送る
        cp_response = asyncio.Event()
        def pmd_cp_handler(sender, data):
            print(f"  [PMD-CP] response: {data.hex()}")
            cp_response.set()

        await client.start_notify(PMD_CP_UUID, pmd_cp_handler)
        await asyncio.sleep(0.3)
        await client.write_gatt_char(PMD_CP_UUID, ECG_START_CMD, response=True)
        await asyncio.wait_for(cp_response.wait(), timeout=5.0)

        print(f"\n収集開始 ({DURATION_SEC}秒)...\n")

        # 指定秒数 or 切断まで待機
        try:
            await asyncio.wait_for(disconnected.wait(), timeout=DURATION_SEC)
            print("\n[警告] デバイス切断を検出")
        except asyncio.TimeoutError:
            pass  # 正常終了 (時間経過)

        # ── 停止 ─────────────────────────────────────────
        if client.is_connected:
            try:
                await client.write_gatt_char(PMD_CP_UUID, ECG_STOP_CMD, response=True)
                await client.stop_notify(HR_MEAS_UUID)
                await client.stop_notify(PMD_DATA_UUID)
                await client.stop_notify(PMD_CP_UUID)
            except Exception as e:
                print(f"[停止] {e}")

    # ── ファイル保存 ──────────────────────────────────────
    session_meta["ecg_samples_total"] = ecg_sample_index
    session_meta["hr_records_total"]  = len(hr_rows)
    session_meta["session_end"]       = datetime.now(timezone.utc).isoformat()

    META_FILE.write_text(json.dumps(session_meta, ensure_ascii=False, indent=2))
    print(f"\nメタデータ保存: {META_FILE}")

    if hr_rows:
        with HR_FILE.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["elapsed_sec", "hr_bpm", "rr_ms"])
            w.writeheader()
            w.writerows(hr_rows)
        print(f"HR保存: {HR_FILE}  ({len(hr_rows)} rows)")

    if ecg_rows:
        with ECG_FILE.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["sample_index", "timestamp_sec", "ecg_uv"])
            w.writeheader()
            w.writerows(ecg_rows)
        print(f"ECG保存: {ECG_FILE}  ({ecg_sample_index} samples)")

    print("\n完了")


asyncio.run(collect())
