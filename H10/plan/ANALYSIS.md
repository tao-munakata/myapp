Analysis layout: constrain grid and fixed-height chart wrappers. Add independent analysis cutoff sliders, filter saved 130 Hz samples before decimation. Default bypass. Saved data already 0.5–40 Hz filtered; disclose limitation. Validate numeric response, short/empty sessions, stale responses. Keep live settings and files unchanged.

## ECG zoom and horizontal navigation
Request: Click a saved analysis ECG location to zoom in; drag left/right to inspect the zoomed waveform.
Scope: `web/static/index.html`, `web/server.py`, `VERSION`, and this plan/work log/handoff.
Behavior: clicking the ECG plot zooms 2× around that time; dragging pans horizontally while preserving zoom; a reset control restores the full session range. Clicking a red RR missing-beat candidate in the HR/RR chart zooms the ECG around that candidate's time. Repeated zoom clicks are bounded by the available samples.
When zooming or panning, fit the ECG Y axis to the visible waveform so outliers elsewhere in the session do not flatten the selected segment.
Show missing-beat candidates as `count / total RR` and percentage. Save RR beat timestamps for newly recorded data; support older files using an estimated timestamp derived from the session filename and elapsed time.
## Raw ECG display
Add analysis controls to show the exact ECG samples received from the sensor or return to the existing filtered recording. Store raw values alongside the existing filtered values for new recordings; preserve the filtered channel and its slider behavior. Older files lack raw values and must be identified as unavailable instead of presenting filtered values as raw.
Keep live filtering and acquisition behavior otherwise unchanged. Empty/one-point waveforms remain non-interactive.
Version: 1.3.0.
Validation: inspect the diff; verify source switching, legacy raw-data availability, timestamp correspondence, zoom bounds, candidate ratio and reset on session change.
