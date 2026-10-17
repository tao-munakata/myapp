"""
Polar H10 Monitor — FastAPI + WebSocket サーバー
"""
import asyncio, threading, queue, time, csv, struct, json
from pathlib import Path
from datetime import datetime, timezone
from typing import Set

import numpy as np
from scipy import signal as scipy_signal
from bleak import BleakClient, BleakScanner
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# ── 設定 ──────────────────────────────────────────────────────
POLAR_H10_ADDR  = "24:AC:AC:1F:BD:C9"
FS              = 130.0
GAP_CRIT_SEC    = 2.5
RECONNECT_DELAY = 6.0
FILE_ROTATE_SEC = 3600
DATA_DIR        = Path("/app/data")
DATA_DIR.mkdir(exist_ok=True)

HR_MEAS_UUID  = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_UUID  = "00002a19-0000-1000-8000-00805f9b34fb"
PMD_CP_UUID   = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"
PMD_DATA_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"
ECG_START_CMD = bytearray([0x02,0x00,0x00,0x01,0x82,0x00,0x01,0x01,0x0E,0x00])
ECG_STOP_CMD  = bytearray([0x03,0x00])

# ── グローバル状態 ─────────────────────────────────────────────
app_state = {
    "running": False, "connected": False,
    "battery": None, "last_bpm": None,
    "session_start": None, "gap_count": 0,
    "status": "停止中",
}
_ble_queue: queue.Queue = queue.Queue()
_ws_queue = None        # asyncio.Queue、startup で初期化
_ble_worker = None
_recorder = None

# ECG フィルタ (サーバーサイド)
_sos = scipy_signal.butter(4, [0.5, 40.0], btype="bandpass", fs=FS, output="sos")
_zi  = scipy_signal.sosfilt_zi(_sos) * 0
_mean_rr = 850.0
_filter_settings = {"low_hz": 0.5, "high_hz": 40.0}
_display_sos = _sos.copy()
_display_zi = _zi.copy()


# ── パーサ ────────────────────────────────────────────────────
def parse_hr(data):
    flags = data[0]
    idx   = 1
    hr    = struct.unpack_from("<H", data, idx)[0] if flags & 0x01 else data[idx]
    idx  += 2 if flags & 0x01 else 1
    rr = []
    if (flags >> 4) & 0x01:
        while idx + 1 < len(data):
            rr.append(round(struct.unpack_from("<H", data, idx)[0] * 1000 / 1024, 2))
            idx += 2
    return hr, rr

def parse_ecg(data):
    if len(data) < 10 or data[0] != 0x00:
        return []
    s, i = [], 10
    while i + 2 < len(data):
        s.append(int.from_bytes(data[i:i+3], "little", signed=True))
        i += 3
    return s


# ── DataRecorder ──────────────────────────────────────────────
class DataRecorder:
    def __init__(self):
        self._ef = self._hf = None
        self._ew = self._hw = None
        self._ecg_idx = 0
        self._ecg_t0  = None
        self._start   = time.time()
        self._rotate_at = self._start + FILE_ROTATE_SEC
        self._open()

    def _open(self):
        self._close()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ep = DATA_DIR / f"ecg_{ts}.csv"
        hp = DATA_DIR / f"hr_{ts}.csv"
        self._ef = open(ep, "w", newline=""); self._ew = csv.writer(self._ef)
        self._hf = open(hp, "w", newline=""); self._hw = csv.writer(self._hf)
        self._ew.writerow(["sample_index", "timestamp_sec", "ecg_uv", "ecg_raw"])
        self._hw.writerow(["elapsed_sec", "hr_bpm", "rr_ms", "timestamp_epoch_sec"])
        self._rotate_at = time.time() + FILE_ROTATE_SEC

    def record_ecg(self, t, raw_samples, filtered_samples):
        if self._ecg_t0 is None:
            self._ecg_t0 = t
        for raw, filtered in zip(raw_samples, filtered_samples):
            self._ew.writerow([self._ecg_idx, round(self._ecg_t0 + self._ecg_idx / FS, 6), filtered, raw])
            self._ecg_idx += 1
        self._ef.flush()
        if time.time() >= self._rotate_at:
            self._open()

    def record_hr(self, t, bpm, rr_list):
        elapsed = t - self._start
        rows = rr_list or [None]
        for i, rr in enumerate(rows):
            beat_time = t - sum(rows[i + 1:]) / 1000 if rr is not None else None
            self._hw.writerow([round(elapsed, 3), bpm, rr,
                               round(beat_time, 6) if beat_time is not None else None])
        self._hf.flush()

    def _close(self):
        for f in [self._ef, self._hf]:
            try:
                f and f.close()
            except Exception:
                pass
        self._ef = self._hf = None

    def close(self):
        self._close()


# ── BLE Worker ────────────────────────────────────────────────
class BLEWorker:
    def __init__(self, q: queue.Queue):
        self.q = q
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()

    def put(self, msg):
        self.q.put(msg)

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ble_loop())

    async def _ble_loop(self):
        while not self._stop.is_set():
            try:
                self.put({"type": "status", "text": "スキャン中..."})
                device = await BleakScanner.find_device_by_address(
                    POLAR_H10_ADDR, timeout=15.0)
                if device is None:
                    self.put({"type": "status",
                              "text": f"デバイス未検出 — {RECONNECT_DELAY:.0f}秒後に再試行"})
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
                self.put({"type": "status", "text": "接続中..."})
                await self._session(device)
            except Exception as e:
                self.put({"type": "status", "text": f"エラー: {e}"})
                self.put({"type": "connected", "value": False})
            if not self._stop.is_set():
                self.put({"type": "status",
                          "text": f"切断 — {RECONNECT_DELAY:.0f}秒後に再接続"})
                await asyncio.sleep(RECONNECT_DELAY)

    async def _session(self, device):
        disconnected  = asyncio.Event()
        last_hr_time  = [None]
        gap_reported  = [False]

        def on_dc(c):
            disconnected.set()
            self.put({"type": "connected", "value": False})
            self.put({"type": "gap", "gap_sec": 0, "gtype": "BLE切断"})

        def hr_handler(_, data):
            bpm, rr_list = parse_hr(bytearray(data))
            self.put({"type": "hr", "bpm": bpm, "rr": rr_list})
            last_hr_time[0] = time.time()
            gap_reported[0] = False

        def ecg_handler(_, data):
            samples = parse_ecg(bytearray(data))
            if samples:
                self.put({"type": "ecg", "samples": samples})

        async with BleakClient(
            device, timeout=40.0, disconnected_callback=on_dc
        ) as client:
            self.put({"type": "connected", "value": True})
            self.put({"type": "status", "text": "接続済み"})
            try:
                bat = await client.read_gatt_char(BATTERY_UUID)
                self.put({"type": "battery", "pct": bat[0]})
            except Exception:
                pass

            await client.start_notify(PMD_DATA_UUID, ecg_handler)
            await client.start_notify(HR_MEAS_UUID, hr_handler)

            cp_ready = asyncio.Event()
            await client.start_notify(PMD_CP_UUID, lambda s, d: cp_ready.set())
            await asyncio.sleep(0.3)
            await client.write_gatt_char(PMD_CP_UUID, ECG_START_CMD, response=True)
            try:
                await asyncio.wait_for(cp_ready.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            self.put({"type": "status", "text": "収集中"})

            async def watchdog():
                while not self._stop.is_set() and not disconnected.is_set():
                    await asyncio.sleep(1.0)
                    if last_hr_time[0] and not gap_reported[0]:
                        since = time.time() - last_hr_time[0]
                        if since >= GAP_CRIT_SEC:
                            self.put({"type": "gap",
                                      "gap_sec": round(since, 1),
                                      "gtype": "心拍停止"})
                            gap_reported[0] = True

            async def wait_stop():
                while not self._stop.is_set() and not disconnected.is_set():
                    await asyncio.sleep(0.5)

            await asyncio.gather(watchdog(), wait_stop())
            if client.is_connected:
                try:
                    await client.write_gatt_char(PMD_CP_UUID, ECG_STOP_CMD, response=True)
                except Exception:
                    pass


# ── WebSocket マネージャ ───────────────────────────────────────
class WsManager:
    def __init__(self):
        self.clients: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, msg: dict):
        dead = set()
        data = json.dumps(msg, ensure_ascii=False)
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self.clients -= dead


manager = WsManager()
app = FastAPI()


@app.on_event("startup")
async def startup():
    global _ws_queue
    _ws_queue = asyncio.Queue()
    asyncio.create_task(_queue_bridge())
    asyncio.create_task(_broadcast_worker())


async def _queue_bridge():
    """スレッドキュー → asyncio キュー"""
    while True:
        try:
            msg = _ble_queue.get_nowait()
            await _ws_queue.put(msg)
        except queue.Empty:
            await asyncio.sleep(0.02)


async def _broadcast_worker():
    """asyncio キュー → WebSocket ブロードキャスト + 状態更新"""
    global _mean_rr, _zi, _display_zi
    while True:
        msg = await _ws_queue.get()
        kind = msg.get("type")

        if kind == "connected":
            app_state["connected"] = msg["value"]
        elif kind == "status":
            app_state["status"] = msg["text"]
        elif kind == "battery":
            app_state["battery"] = msg["pct"]
        elif kind == "hr":
            app_state["last_bpm"] = msg["bpm"]
            for rr in msg.get("rr", []):
                _mean_rr = 0.9 * _mean_rr + 0.1 * rr
            if _recorder:
                _recorder.record_hr(time.time(), msg["bpm"], msg.get("rr", []))
        elif kind == "ecg":
            # サーバーサイドバンドパスフィルタ
            raw_samples = msg["samples"]
            msg["raw_samples"] = raw_samples.copy()
            arr = np.array(raw_samples, dtype=float)
            filt, _zi = scipy_signal.sosfilt(_sos, arr, zi=_zi)
            display, _display_zi = scipy_signal.sosfilt(
                _display_sos, arr, zi=_display_zi)
            msg["samples"] = [round(float(v), 1) for v in display]
            if _recorder:
                _recorder.record_ecg(time.time(), raw_samples, [round(float(v), 1) for v in filt])
        elif kind == "gap":
            app_state["gap_count"] += 1
            msg["ts"] = datetime.now().strftime("%H:%M:%S")

        await manager.broadcast(msg)


# ── REST API ──────────────────────────────────────────────────

class FilterSettings(BaseModel):
    low_hz: float = Field(ge=0.1, le=10.0, allow_inf_nan=False)
    high_hz: float = Field(ge=15.0, le=60.0, allow_inf_nan=False)


@app.get("/api/filter")
async def api_filter():
    return dict(_filter_settings)


@app.post("/api/filter")
async def api_set_filter(settings: FilterSettings):
    global _display_sos, _display_zi, _filter_settings
    new_settings = {"low_hz": settings.low_hz, "high_hz": settings.high_hz}
    if new_settings != _filter_settings:
        sos = scipy_signal.butter(
            4, [settings.low_hz, settings.high_hz],
            btype="bandpass", fs=FS, output="sos")
        _display_sos = sos
        _display_zi = scipy_signal.sosfilt_zi(sos) * 0
        _filter_settings = new_settings
        await manager.broadcast({"type": "filter", **new_settings})
    return {"ok": True, **_filter_settings}


@app.post("/api/start")
async def api_start():
    global _ble_worker, _recorder, _zi, _mean_rr, _display_zi
    if app_state["running"]:
        return {"ok": False, "msg": "すでに収集中"}
    app_state["running"] = True
    app_state["gap_count"] = 0
    app_state["session_start"] = time.time()
    _zi = scipy_signal.sosfilt_zi(_sos) * 0   # フィルタ状態リセット
    _mean_rr = 850.0
    _display_zi = scipy_signal.sosfilt_zi(_display_sos) * 0
    _recorder = DataRecorder()
    _ble_worker = BLEWorker(_ble_queue)
    _ble_worker.start()
    return {"ok": True}


@app.post("/api/stop")
async def api_stop():
    global _ble_worker, _recorder
    if not app_state["running"]:
        return {"ok": False, "msg": "収集していません"}
    app_state["running"] = False
    app_state["connected"] = False
    if _ble_worker:
        _ble_worker.stop()
        _ble_worker = None
    if _recorder:
        _recorder.close()
        _recorder = None
    app_state["status"] = "停止中"
    await manager.broadcast({"type": "status", "text": "停止中"})
    await manager.broadcast({"type": "connected", "value": False})
    return {"ok": True}


@app.get("/api/status")
async def api_status():
    elapsed = None
    if app_state["session_start"] and app_state["running"]:
        e = int(time.time() - app_state["session_start"])
        h, r = divmod(e, 3600)
        m, s = divmod(r, 60)
        elapsed = f"{h:02d}:{m:02d}:{s:02d}"
    return {**app_state, "elapsed": elapsed, "filter": dict(_filter_settings)}


@app.get("/api/sessions")
async def api_sessions():
    files = sorted(DATA_DIR.glob("ecg_*.csv"), reverse=True)
    result = []
    for f in files:
        stat = f.stat()
        stem = f.stem.replace("ecg_", "")
        hr_path = f.parent / f"hr_{stem}.csv"
        hr_kb = round(hr_path.stat().st_size / 1024, 1) if hr_path.exists() else None
        result.append({
            "stem": stem,
            "name": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "hr_size_kb": hr_kb,
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%m/%d %H:%M"),
        })
    return result


@app.delete("/api/session/{stem}")
async def api_session_delete(stem: str):
    deleted = []
    errors  = []
    for prefix in ("ecg_", "hr_"):
        path = DATA_DIR / f"{prefix}{stem}.csv"
        if path.exists():
            try:
                path.unlink()
                deleted.append(path.name)
            except Exception as e:
                errors.append(f"{path.name}: {e}")
    if errors:
        return JSONResponse({"ok": False, "errors": errors}, status_code=500)
    return {"ok": True, "deleted": deleted}


@app.get("/api/session/{stem}/hr")
async def api_session_hr(stem: str):
    path = DATA_DIR / f"hr_{stem}.csv"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    t_list, hr_list, rr_list, rr_t = [], [], [], []
    rows = []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    first_elapsed = next((float(row["elapsed_sec"]) for row in rows if row.get("elapsed_sec")), 0.0)
    try:
        stem_epoch = datetime.strptime(stem, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        stem_epoch = 0.0
    estimated_start_epoch = stem_epoch - first_elapsed
    for row in rows:
        t_list.append(float(row["elapsed_sec"]))
        hr_list.append(int(row["hr_bpm"]))
        if row["rr_ms"] and row["rr_ms"] != "None":
            rr_list.append(float(row["rr_ms"]))
            timestamp = row.get("timestamp_epoch_sec")
            rr_t.append(float(timestamp) if timestamp not in (None, "", "None")
                        else estimated_start_epoch + float(row["elapsed_sec"]))
    return {"t": t_list, "hr": hr_list, "rr": rr_list, "rr_t": rr_t}


@app.get("/api/session/{stem}/ecg")
async def api_session_ecg(stem: str,
    low_hz: float = Query(default=None, ge=0.1, le=10.0),
    high_hz: float = Query(default=None, ge=15.0, le=60.0),
    raw: bool = Query(default=False)):
    path = DATA_DIR / f"ecg_{stem}.csv"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    if (low_hz is None) != (high_hz is None):
        return JSONResponse({"error": "Specify both cutoff frequencies"}, status_code=422)
    t_list, v_list = [], []
    with path.open() as f:
        reader = csv.DictReader(f)
        raw_available = "ecg_raw" in (reader.fieldnames or [])
        for row in reader:
            t_list.append(float(row["timestamp_sec"]))
            use_raw = raw and raw_available and row.get("ecg_raw") not in (None, "", "None")
            v_list.append(float(row["ecg_raw"] if use_raw else row["ecg_uv"]))
    if low_hz is not None and v_list:
        sos = scipy_signal.butter(4, [low_hz, high_hz], btype="bandpass", fs=FS, output="sos")
        zi = scipy_signal.sosfilt_zi(sos) * v_list[0]
        filtered, _ = scipy_signal.sosfilt(sos, np.asarray(v_list), zi=zi)
        v_list = filtered.tolist()
    t0 = t_list[0] if t_list else 0
    return {"t": [round(t - t0, 3) for t in t_list[::5]], "ecg": v_list[::5],
            "start_epoch": t0, "raw_available": raw_available, "raw_displayed": raw and raw_available}


# ── WebSocket ─────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # 接続直後に現在状態を送信
    await ws.send_text(json.dumps({
        "type": "init",
        "state": {
            "running": app_state["running"],
            "connected": app_state["connected"],
            "battery": app_state["battery"],
            "last_bpm": app_state["last_bpm"],
            "gap_count": app_state["gap_count"],
            "status": app_state["status"],
            "filter": dict(_filter_settings),
        }
    }))
    try:
        while True:
            await ws.receive_text()   # keep-alive (クライアントからは何も来ない)
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── 静的ファイル ──────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
