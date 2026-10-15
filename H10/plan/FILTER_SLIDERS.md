# Live ECG filter sliders
Request: adjustable ECG filters at top of browser live screen.
Scope: web/server.py and web/static/index.html.
Two cutoff sliders: high-pass 0.1–10 Hz and low-pass 15–60 Hz; default 0.5–40 Hz.
Shared server setting; synchronize connected browsers and reset live history on change.
Keep recording filter fixed at 0.5–40 Hz and existing analysis behavior.
Validate bounds, API synchronization and numerical filter response before deployment.
