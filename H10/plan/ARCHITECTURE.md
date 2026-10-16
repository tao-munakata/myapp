# Architecture

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
