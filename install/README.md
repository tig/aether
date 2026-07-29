# Install / update (Aether)

**Writing mode:** Technical (STE bias).

## Host gate (C plate)

1. Configure the host build:

```text
cmake -S host -B build/host
```

2. Build and run host tests:

```text
cmake --build build/host --target host_test
```

## AFR gauge mockup (spec learning)

1. Run the mockup stream:

```text
python -m mockup
```

2. Run unit tests:

```text
python -m pytest mockup/tests -q
```

3. Open the graphical mockup: `mockup/gauge.html` in a browser.

The mockup uses simulated AFR only.

Mockup acceptance cues:

- Circular arc LEDs: green near stoich, amber in transition, red at rich and lean ends.
- Scale 8–20.
- Large center AFR to one decimal.
- Lambda to the right of the value (no `AIR/FUEL RATIO` under-text).

## Deploy (metal — after operator confirm)

1. Inspect the device:

```text
silico inspect --port COMx
```

2. Deploy when the operator confirms:

```text
silico deploy --port COMx --yes --verify --reset
```

Requirements:

- ESP-IDF is installed (`idf.py` or `IDF_PATH`).
- Target board is ESP32-S3 1.8″ AMOLED (B0F242GFHK class).

The full AMOLED product face is not required for the mockup pass.
