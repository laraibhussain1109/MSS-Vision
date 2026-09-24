# MSS Vision — Industrial Process Validation

MSS Vision is a ready-to-run, deterministic OpenCV/PyQt6 poka-yoke station. It watches normalized rectangular or polygonal ROIs, confirms HSV occupancy over time, emits a single event only on a confirmed **ABSENT → PRESENT** transition, and validates those events against any engineer-defined sequence. A failed cycle remains NG until reset.

## Capabilities

- Dark, scalable operator HMI with live overlays, status card, expected step, sequence strip, and event timeline.
- Camera, video-file, and RTSP sources on a dedicated `QThread`, automatic reconnect, and latest-frame processing without a queue.
- GUI ROI setup for rectangles and polygons. Coordinates are normalized to the source frame, so resizing and letterboxing do not shift inspection regions.
- Per-ROI names, requirement/order, threshold, presence/absence debounce, HSV bounds, morphology, and live original/mask/result calibration.
- Generic finite-state sequence engine, simultaneous-event rejection, invalid-start protection, latched NG, and manual/automatic cycles.
- Engineering mode with occupancy, candidate/stable states and frame information; clearly marked manual simulation controls.
- SQLite cycle/event traceability, annotated PASS/NG images, searchable history, event detail, and Excel export.
- JSON product profiles, saved reference images, rotating logs, optional ArUco readiness, and extension interfaces for future detectors.

> **Demo safety:** `profiles/blue_clip_demo.json` contains A/B/C definitions but intentionally contains **no production ROI coordinates**. Simulation mode is enabled so the sequence engine can be evaluated immediately. Draw all ROIs on the real fixture image before camera inspection.

## Requirements

- Python **3.11** (3.10+ is normally compatible)
- Windows 10/11 or modern Linux
- USB/UVC camera, video file, or RTSP stream

## Windows installation

```bat
cd MSS-Vision
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Linux equivalents use `python3 -m venv venv`, `source venv/bin/activate`, then the same install/start commands.

## First-time engineering workflow

1. **Launch** with `python main.py`. The bundled demo loads safely and attempts camera 0; camera failure does not close the app.
2. Select **CAMERA**. Enter `0`–`5`, browse to a video, or paste an RTSP URL. Configure resolution/FPS and supported camera controls, save, and allow reconnect.
3. Place an empty production part in its fixture and choose **CAPTURE REFERENCE**. Alternatively use **Profiles → Load Reference Image**.
4. Choose **EDIT ROIs**. Select Rectangle or Polygon. Drag a rectangle, or click polygon vertices and double-click the final point.
5. Complete the ROI property dialog: unique name, display name, required/order flags, occupancy threshold, and confirmation times. Repeat for every clip.
6. Select each ROI and choose **Calibrate HSV**. Compare Original, HSV Mask and Final Detection. Adjust sliders/spin boxes live. **AUTO SAMPLE COLOR** estimates robust bounds from saturated pixels; fine-tune afterward. Keep the empty ROI safely below threshold and installed clip safely above it.
7. Use **Engineering → Edit Sequence** and drag items into the required order. A/B/C are not special; any number and naming scheme are supported.
8. In **SETTINGS**, choose manual/automatic cycles, the simultaneous-event window, alignment mode, snapshot preferences, audio, and simulation state.
9. Use **Profiles → Save Profile As**. Product setup now lives in JSON and normal use requires no source edits.

## Operator workflow

1. Load an empty part. Stable initial states are established before events are accepted; clips already present at launch never become insertion events.
2. In manual mode, press **START INSPECTION** (`F5`). In automatic mode a cycle starts only after valid empty start conditions.
3. Insert only the yellow **EXPECTED** clip. A confirmed insertion turns green and advances the expected step.
4. Correct completion produces a green PASS and saves traceability. A wrong or effectively simultaneous insertion immediately produces a red, latched NG.
5. Remove/replace the part and press **RESET CYCLE** (`F7`). The station shows **WAITING FOR PART RESET** while required clips remain present.

`F6` stops inspection and `F8` opens ROI setup. Operator mode stays clean; Engineering mode adds occupancy and temporal state details.

## Detection and timing

Each ROI is converted to HSV and segmented with its saved bounds. Opening, closing, erosion and dilation are applied; occupancy is colored valid pixels divided by polygon-mask pixels. Occupancy above the per-ROI threshold is a PRESENT candidate. It must remain unchanged for `presence_ms`; disappearance must remain unchanged for the longer `absence_ms`. UNKNOWN/occluded observations freeze the confirmed state. Only a confirmed ABSENT→PRESENT transition creates one insertion event.

Events inside the configured simultaneous window cause NG because chronology cannot be proven. Sequence errors also latch NG; adding the missing clip later cannot convert the cycle to PASS.

## Profiles, records, and diagnostics

- Profiles: `profiles/*.json`
- Reference images: `profiles/*_reference.jpg` (or an engineer-selected path)
- Database: `inspection_data/inspections.sqlite3`
- Annotated snapshots: `inspection_data/PASS/` and `inspection_data/NG/`
- Rotating application logs: `logs/mss_vision.log`

Open **HISTORY** to search/filter cycles, double-click a row for its event timeline, and choose **EXPORT TO EXCEL**. The workbook contains cycle, profile, timestamps, duration, required/detected sequences, result, reason, and image path.

## Alignment and future integration

`FrameAligner` provides NONE and ArUco marker validation modes. NONE is recommended for a fixed fixture. ArUco requires OpenCV builds exposing `cv2.aruco`; an unavailable or incomplete marker set reports failure rather than guessing. The `BaseDetector` interface isolates detection from temporal filtering and sequence logic, allowing later template/YOLO detectors, hand-occlusion modules, barcode/PLC/IO adapters, operator login, or server storage without rewriting cycle validation.

## Tests

```bat
python -m pytest -q
python -m compileall -q app vision process storage widgets main.py
```

For a headless launch smoke test set `QT_QPA_PLATFORM=offscreen`; a real station should use the normal display backend.
