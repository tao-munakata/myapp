# Implementation

## ECG-only live view
1. Add a dedicated ECG-only tab and full-size responsive waveform chart.
2. Feed it the same filtered rolling buffer as the standard live chart.
3. Add a labeled seconds axis and selectable 5/10/20/30-second rolling window, retaining a 10-second view in the standard live chart.
4. Include exact received samples in ECG WebSocket messages and add filtered/raw mode selection for the ECG-only chart.
5. Make live filter sliders available on the ECG-only tab; disable them in raw mode and retain standard-dashboard filtering.
6. Document the UI/data-flow change in `WORKLOG.md` and `HANDOFF.md`.

1. Convert the analysis ECG chart to explicit `{x: elapsedSeconds, y: sample}` points with a linear time axis.
2. Add click-centered zoom, mouse drag panning, and a reset button; keep the range within the selected session.
3. Persist RR beat timestamps, expose them from the HR endpoint, and use them to make red candidate points clickable.
4. Display the candidate count, total RR count, and candidate percentage.
5. Save received raw ECG samples beside the current filtered samples, expose source selection through the ECG endpoint, and add raw/filtered controls in analysis.
6. Reset the view when a session is loaded and disable navigation for fewer than two points.
7. Bump `VERSION` to 1.3.0 and record implementation/verification in `WORKLOG.md` and `HANDOFF.md`.
