# Install / update (Aether)

## Host gate (C plate)

```text
cmake -S host -B build/host
cmake --build build/host --target host_test
```

## AFR gauge mockup (spec learning)

```text
python -m mockup
python -m pytest mockup/tests -q
# Graphical: open mockup/gauge.html in a browser
```

Simulated AFR only. What “good” looks like for the mockup: circular arc LEDs
(green near stoich, amber transition, red at rich/lean ends), scale 8–20, large
center AFR to one decimal, **AIR/FUEL RATIO** label.

## Deploy (metal — after operator confirm)

```text
silico inspect --port COMx
silico deploy --port COMx --yes --verify --reset
```

Requires ESP-IDF (`idf.py` or `IDF_PATH`). Target board: ESP32-S3 1.8″ AMOLED
(B0F242GFHK class). Full AMOLED product face is not required for the mockup pass.
