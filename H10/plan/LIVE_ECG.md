# Live ECG layout fix
Request: Browser live ECG extends outside the screen.
Scope: web/static/index.html live layout and header wrapping only.
Keep acquisition, stored data and analysis unchanged.
Implementation: constrain grid tracks/cards/chart containers; stack log on narrow screens.
Validation: inspect diff and verify served HTML matches source.
