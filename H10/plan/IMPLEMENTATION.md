# Implementation

1. Convert the analysis ECG chart to explicit `{x: elapsedSeconds, y: sample}` points with a linear time axis.
2. Add click-centered zoom, mouse drag panning, and a reset button; keep the range within the selected session.
3. Persist RR beat timestamps, expose them from the HR endpoint, and use them to make red candidate points clickable.
4. Display the candidate count, total RR count, and candidate percentage.
5. Save received raw ECG samples beside the current filtered samples, expose source selection through the ECG endpoint, and add raw/filtered controls in analysis.
6. Reset the view when a session is loaded and disable navigation for fewer than two points.
7. Bump `VERSION` to 1.3.0 and record implementation/verification in `WORKLOG.md` and `HANDOFF.md`.
