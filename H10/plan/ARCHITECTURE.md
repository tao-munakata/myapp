# Architecture

## ECG-only live view
- Add a dedicated tab that displays only the live ECG waveform at a large size for simultaneous visual observation and manual pulse checking.
- Reuse the existing WebSocket samples and display filter; do not change acquisition, recording, or analysis behavior.
- Keep the standard live dashboard intact. The ECG-only view has its own responsive chart and a brief note that manual pulse comparison is observational, not a diagnostic result.
- Show a labeled seconds axis in the ECG-only chart and let the user choose a rolling 5, 10, 20, or 30-second window. Keep the standard live chart at its current 10-second range.
- Make the live filter sliders available from the ECG-only tab, and add a mode switch for filtered display versus exact received samples. Raw mode applies only to the ECG-only chart; preserve filtered display in the standard dashboard and recording path.
- Include received raw samples alongside the existing filtered WebSocket samples; do not change the stored data format or acquisition path.

## Analysis ECG zoom, pan, and missing-beat candidates
- Keep the feature in the existing Chart.js ECG chart in `web/static/index.html`.
- Use elapsed seconds as a linear X axis so the visible range can be set directly.
- A click zooms in 2× around its X coordinate; dragging changes the visible X range by the same pixel distance while preserving its width.
- Bound the visible range to the session's full time extent, fit Y to the visible ECG samples, and provide a reset action.
- Give each saved RR point a wall-clock beat timestamp, and include it in the HR API response. New recordings store this timestamp in the HR CSV; older recordings estimate it from their filename and elapsed time.
- Clicking a red missing-beat RR point sets a local ECG view centered on its timestamp.
- Show candidate count against total RR count and as a percentage.
- Store the exact received ECG samples alongside the existing filtered samples. An analysis source toggle selects raw or filtered data; old files report that raw data is unavailable.
- Acquisition flow, live display filtering, and HR/RR chart behavior remain unchanged. The ECG CSV gains a raw-value column while retaining the existing filtered-value column.
