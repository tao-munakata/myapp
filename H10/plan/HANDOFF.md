
## 20261016T051552 Live ECG
Browser live layout corrected; requires page reload. Acquisition and data unchanged. Visual browser verification pending (browser connection unavailable).

## 2026-10-16 Filter sliders deployed
User authorized restart. Container server.py and static/index.html updated; restarted successfully. API update/read/reset verified; default 0.5–40 Hz restored. Numerical response, bounds, recording isolation, Python/JS syntax and served HTML hash checks passed. Browser visual verification pending. Collection stopped; use Start to resume.

## 2026-10-16 Analysis layout and sliders
Deployed fixed-height chart wrappers, shrinkable grid and independent analysis sliders with original-waveform reset. Filter applied at 130 Hz before display decimation. Saved files and live filter settings preserved. Python/JS syntax, numerical output, empty/short sessions, live API bounds and served HTML hash verified. Browser visual verification unavailable. Backup suffix 20261016T052734.
## 2026-10-17 Analysis ECG zoom and pan
Implemented in `web/static/index.html`; `VERSION` is 1.1.0.
- Click in the ECG plot to zoom in 2× around that time.
- Drag horizontally to pan at the current zoom level; the range stays inside the session.
- Use 「全体表示」 to restore the session range. Loading another session resets the view.
- Empty and one-point waveform responses do not enable zoom/pan.

The running container initially served an older HTML file (no zoom controls). Rebuilt/restarted the container while collection was stopped; verified the served HTML includes the new controls and `/api/status` responds. Browser interaction verification remains pending. No API or saved data changes.
## 2026-10-17 Clickable missing-beat candidates and percentage
Implementation updates `web/server.py` and `web/static/index.html`; `VERSION` is 1.2.0.
- Red RR candidate points zoom the ECG to approximately 2.5 seconds on either side of the event; horizontal drag and full-session reset continue to work.
- Summary displays candidate count / RR count and percentage.
- New HR CSV rows carry `timestamp_epoch_sec`; old rows are read with an estimated session offset from file stem and first elapsed value.
- Rebuilt/restarted while collection was stopped. Confirmed served page includes click guidance and candidate percentage code; status endpoint responds. Actual browser click behavior remains unverified.
## 2026-10-17 ECG zoom vertical scale fix
The zoomed ECG now fits its Y axis to visible samples, avoiding compression from outliers elsewhere in the recording. VERSION is 1.2.1. Rebuilt/restarted while collection was stopped; served page and API status confirmed. Browser appearance remains to be confirmed.
## 2026-10-17 Raw ECG source toggle
New captures store original received ECG samples alongside the existing filtered channel. Analysis can switch to raw data and back to filtered data. VERSION is 1.3.0. Deployed; page controls and API respond. However, `/data/H10` is empty and the API lists zero sessions after container replacement. Previous session files were listed before the replacement but are not present in the current host mount or accessible workspace paths. Recovery/cause is unresolved; new recordings can be saved once collection resumes.
