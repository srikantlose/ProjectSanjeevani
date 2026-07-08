# Project Sanjeevani — End-to-End Build Plan (rev. 2, 2026-07-08)

This document is the single source of truth for building Project Sanjeevani. It is written so that an AI coding agent (or a human) with no prior context can open this file, open `PROGRESS.md`, and start building at the first unchecked task — no additional design decisions required. Read this whole file once before writing any code. Then work top-to-bottom through §13.

**Revision note (rev. 2):** E0–E2 and E3-T1/T2 are complete (see `PROGRESS.md`). This revision restructures everything from E3-T3 onward with much deeper, non-ambiguous specifications, fixes gaps found in a full codebase review (missing config system, missing ROI-tool task, underspecified engine wiring, missing CORS, unpinned seed data), and incorporates three user decisions dated 2026-07-08:
1. **Datasets:** everything scriptable gets a script; registration/manual downloads become a precise user checklist (`docs/data_checklist.md`). Build tasks that need that data pause with **USER ACTION REQUIRED**; everything else proceeds.
2. **Occluded rider-down demo clip:** build and gate-test against the best available public/placeholder clip now; the user stages/films the ideal occluded scenario later — swapping it in must be a config-only change.
3. **Near-miss study:** runs on public long-form traffic-cam footage (non-Bengaluru acceptable), honestly labeled in the report.

---

## §1. Project Overview & How To Use This Document

### 1.1 What this project is

Sanjeevani is an AI system that watches traffic camera video, detects probable road accidents within seconds, has a human operator confirm them with one tap, classifies severity, and drives a simulated emergency response: ambulance dispatch on a real Bengaluru map, a green-corridor signal sequence along the route, and a hospital pre-alert. It is a solo final-year academic project. The deliverable is a **working, rehearsed, five-minute live demo** plus a written report — not a production system.

### 1.2 The core loop

**Detect → Verify → Triage → Dispatch → Resolve.**

1. **Detect** — a Python video-analysis engine watches a camera feed (a video file, played back at real-time pace to simulate a live camera) and raises an `IncidentCandidate` when its signal-fusion logic crosses a threshold.
2. **Verify** — a human operator, in the control-room dashboard, sees a short clip and taps Confirm or Reject.
3. **Triage** — the engine attaches a severity label (LOW/MEDIUM/HIGH) and human-readable reasons at detection time.
4. **Dispatch** — on confirm, the backend picks the nearest simulated ambulance, routes it on a real Bengaluru road network, and starts moving it.
5. **Resolve** — signals along the ambulance's route turn green in sequence (green corridor) and the destination hospital gets a pre-alert card with severity and live ETA.

### 1.3 The two novel claims + the prevention chapter

1. **Crowd-as-signal detection** (`services/detection/signals/crowd.py`, built): sudden pedestrian clustering *on the carriageway* as an independent accident signal — fires when the impact itself is occluded. The single most important thing to demonstrate (GATE-A in E8-T3).
2. **Rider-down + severity triage** (`services/detection/signals/rider_down.py`, built): detects a two-wheeler rider down specifically, always emits severity with reasons.
3. **Near-miss analytics** (E9-T3): Post-Encroachment-Time-proxy conflict counting on long-form traffic footage — the prevention chapter of the report.

### 1.4 Scope discipline: Build / Simulate / Describe

**Build (real code):** detection (direct + crowd + rider-down + severity), control-room dashboard with one-tap verify.
**Simulate (real code, mock actors):** ambulance dispatch on real routing, green corridor, hospital pre-alert, one highway scenario.
**Describe (docs only, never code):** 112/108 integration, live police feeds, signal-preemption hardware, FIR/insurance automation, citizen apps, statewide rollout → `docs/future_work.md`.

If a new idea comes up mid-build it goes to `docs/future_work.md`, not the codebase.

### 1.5 The demo storyline (design everything backwards from this)

1. Junction footage plays. A two-wheeler goes down, partially occluded.
2. Within seconds the system flags an incident; the "why" panel shows crowd clustering + flow collapse with the direct collision signal weak/absent.
3. Severity triage appears: "rider down — HIGH".
4. Operator watches a ~15 s evidence clip, taps Confirm.
5. Ambulance dispatches on the Bengaluru map; corridor junctions flip green in sequence; hospital console lights up with severity + ETA; an on-screen stopwatch shows crash-to-dispatch time.
6. Cut to highway clip: stationary vehicle in a live lane, same engine, highway mode.
7. Closing: `/metrics` view with measured latency, TPR/FAR, occlusion-robustness count, simulated crash-to-dispatch vs. the 8–15 min call-based baseline.

### 1.6 Instructions for whoever (or whatever) builds this

- **Work one task at a time**, in the exact order in §13. Each task lists Goal / Files / Steps / **Acceptance check**. Do not start a task until the previous one's acceptance check passes.
- **Tick the box in `PROGRESS.md`** immediately after acceptance passes; add a deviation-log entry if anything differed from this plan.
- **Never hardcode a tunable value** — every threshold lives in YAML (§7.9). If a threshold must change to make real footage work, change the YAML and log it.
- **Do not refactor ahead of the task list.**
- **Commit after every passing task and push to `origin main`** (`https://github.com/srikantlose/ProjectSanjeevani.git`). Plain engineering-voice commit messages, no AI attribution.
- **Run the full test suite** (`venv\Scripts\python.exe -m pytest tests/ -q`) before every commit; all tests must pass.
- **USER ACTION REQUIRED tasks** (E8-T1; parts of E9-T3): prepare everything preparable (scripts, checklist docs, directory layout), then stop and tell the user exactly what to do. Continue with any later task that does not depend on the missing data; resume the paused task when the data appears.
- **Frontend is minimal-UI only** (standing user directive, 2026-07-07): functional data-wiring, semantic markup, structural layout classes only (flex/grid/gap/padding). **No colors, theming, typography choices, or visual polish** — the user will supply design specs later (E10-T5, BLOCKED).
- When a section below says "as built", the code already exists and passed acceptance — do not rewrite it; later tasks extend it exactly as specified.

---

## §2. Locked Decisions (as actually built)

| Decision | Value |
|---|---|
| Compute | Local NVIDIA RTX 4060 (8 GB), driver 591.74. CUDA verified: `torch.cuda.is_available()` → True. |
| Python | **3.13.7** (plan originally said 3.11; 3.13 is what exists on the machine and everything works — logged deviation). venv at `venv/`, activate with `venv\Scripts\Activate.ps1`; in bash use `./venv/Scripts/python.exe`. |
| PyTorch | 2.11.0+cu128 via `--index-url https://download.pytorch.org/whl/cu128`. |
| Detection | Ultralytics YOLO11 (`models/yolo11s.pt`, `models/yolo11s-pose.pt`, downloaded by `scripts/download_models.py`) + built-in ByteTrack. `lap` is a required dep (in requirements.txt). |
| Backend | FastAPI + SQLite (SQLAlchemy) at `data/sanjeevani.db` (path overridable via env `SANJEEVANI_DB_PATH` — tests use tmp DBs). Simulators = asyncio tasks inside the API process. |
| Dashboard | React 18 + Vite + TypeScript + **Tailwind v4** (CSS-first: `@tailwindcss/vite` plugin + `@import "tailwindcss";` in `src/index.css`; there is **no** `tailwind.config.js`) + MapLibre GL + Zustand. Node 24 / npm 11. |
| Ports | API `:8000` (uvicorn), dashboard dev `:5173` (vite). CORS: API allows origin `http://localhost:5173`. |
| IDs | The **engine** mints incident IDs: `inc_{UTC:%Y%m%d%H%M%S}_{seq:03d}` (seq = per-engine-run counter). The API accepts them as primary keys. |
| Connectivity | Internet OK; every network dependency has an offline fallback (tile cache proxy, prefetched route GeoJSON, committed junction seed). |
| Git | Remote `origin` = github.com/srikantlose/ProjectSanjeevani.git, branch `main`, push after every task. |
| OS | Windows 11. Bash tool paths: `/c/Users/user/Desktop/PROJECTS 2026/Project Sanjeevani`. ffmpeg: install via `winget install Gyan.FFmpeg` if `shutil.which("ffmpeg")` is None (E4-T3 handles absence gracefully). |

---

## §3. System Architecture

Three server-side processes + the browser (3 windows):

```
┌─────────────────────────┐   POST /api/incidents/candidate   ┌───────────────────────────────┐
│ Detection Engine        │ ─────────────────────────────────▶ │ Backend API (FastAPI, :8000)  │
│ services/detection      │      (engine mints incident id)    │ services/api                  │
│  video_source (paced)   │                                    │  SQLite data/sanjeevani.db    │
│  detector (YOLO11+BT)   │                                    │  WS hub /ws ──────────────────┼──▶ Dashboard (:5173)
│  tracker_ctx            │                                    │  sim/: ambulance, corridor,   │    /control /dispatch
│  signals/* (5 modules)  │                                    │        hospital (asyncio)     │    /hospital /metrics
│  fusion → severity      │                                    │  /media  → data/clips         │
│  evidence (ring buffer) │                                    │  /scenario_media → processed  │
│  emitter (+disk queue)  │                                    │  /tiles/{z}/{x}/{y}.png cache │
└─────────────────────────┘                                    └───────────────────────────────┘
```

**Event flow for one incident:** engine fusion crosses threshold → severity assessed → evidence clip+snapshot written to `data/clips/{incident_id}/` → engine POSTs candidate JSON (§8.2.1) → API persists (`incidents` + `incident_signals`) status `PENDING_VERIFICATION`, broadcasts `incident.new` (paths converted to `/media/...` URLs) → operator Confirms in dashboard → `POST /api/incidents/{id}/verify` → status `CONFIRMED`, then `sim.dispatch_incident()`: nearest idle ambulance + hospital selection + route → `dispatches` row, status `DISPATCHED`, broadcast `incident.updated` **with embedded dispatch object (route included)** → mover ticks 1 Hz broadcasting `ambulance.position`; corridor sequencer broadcasts `corridor.updated` on state changes; at `AT_SCENE` a single `hospital.alert` fires → `TO_HOSPITAL` → `ARRIVED` → incident `RESOLVED` (broadcast `incident.updated`).

**Incident state machine:** `PENDING_VERIFICATION → CONFIRMED → DISPATCHED → RESOLVED`, or `PENDING_VERIFICATION → REJECTED`. (The finer-grained EN_ROUTE/AT_SCENE/TO_HOSPITAL states live on the **dispatch**, not the incident: dispatch `state ∈ {TO_SCENE, AT_SCENE, TO_HOSPITAL, ARRIVED}`.)

---

## §4. Tech Stack (as built + planned)

Python (`requirements.txt`, all installed): ultralytics, lap, opencv-python, supervision, scikit-learn, numpy, scipy, shapely, pyyaml, httpx, pytest, fastapi, uvicorn[standard], sqlalchemy, pydantic, websockets. Torch/torchvision installed separately (cu128).

Node (`apps/dashboard/package.json`): react, react-dom, react-router-dom, maplibre-gl, zustand; dev: vite, typescript, tailwindcss v4 + @tailwindcss/vite.

**Routing:** OSRM public server `https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson` with a 2 s timeout; on any failure fall back to committed GeoJSON in `data/routes/` (prefetched by `scripts/prefetch_routes.py`, §9.2).

**Map tiles:** browser never hits OSM directly. API proxies `GET /tiles/{z}/{x}/{y}.png` → `https://tile.openstreetmap.org/{z}/{x}/{y}.png` with header `User-Agent: SanjeevaniDemo/1.0 (academic project)` (OSM tile policy requires a UA), caching each PNG at `data/tile_cache/{z}/{x}/{y}.png` forever. One rehearsal warms the whole demo tile set.

**Junction seed:** `scripts/seed_junctions.py` queries Overpass once at build time (§9.1); committed output `data/seed/junctions.json` is the runtime source. Overpass is never called at demo time.

---

## §5. Repository Layout (as built; files marked ➕ are created by remaining tasks)

```
Project Sanjeevani/
├── plan.md  PROGRESS.md  README.md  .gitignore  requirements.txt
├── pytest.ini ➕(E4-T0)
├── configs/
│   ├── cameras/
│   │   ├── vtest_highway_test.yaml ➕(E4-T5, committed test config)
│   │   ├── junction_cam.yaml ➕(E8-T2)   └── highway_cam.yaml ➕(E8-T2)
│   ├── modes/
│   │   ├── city.yaml ➕(E4-T0)           └── highway.yaml ➕(E4-T0)
│   └── scenarios/
│       ├── scenario1_junction.yaml ➕(E8-T2)  └── scenario2_highway.yaml ➕(E8-T2)
├── data/
│   ├── raw/ (gitignored)  processed/  clips/ (gitignored)  queue/ (gitignored)
│   ├── manifests/eval_manifest.csv ➕(E8-T1)
│   ├── routes/*.geojson ➕(E6-T2)   tile_cache/ (gitignored)
│   └── seed/{hospitals,ambulances,junctions}.json ➕(E6-T1)
├── models/ (gitignored; yolo11s.pt, yolo11s-pose.pt present)
├── services/
│   ├── detection/
│   │   ├── video_source.py ✔  detector.py ✔  tracker_ctx.py ✔  engine.py ✔(rewired E4-T5)
│   │   ├── config.py ➕(E4-T0)  signal_factory.py ➕(E4-T0)
│   │   ├── fusion.py ➕(E4-T1)  severity.py ➕(E4-T2)  evidence.py ➕(E4-T3)  emitter.py ➕(E4-T4)
│   │   └── signals/ base.py ✔ collision.py ✔ rider_down.py ✔(pose E3-T3) crowd.py ✔ flow.py ✔ stationary.py ✔
│   └── api/ ➕(E5)
│       ├── main.py  db.py  models.py  schemas.py  ws.py  seed.py
│       ├── routers/ incidents.py  hospitals.py  ambulances.py  metrics.py  tiles.py
│       └── sim/ geo.py  routing.py  ambulance.py  corridor.py  hospital.py
├── apps/dashboard/  (Vite scaffold ✔; src/{views,components,store,lib,types} filled in E7)
├── eval/ run_eval.py ➕(E9-T1)  metrics.py ➕(E9-T1)  results/ (gitignored)
│   └── near_miss/ conflicts.py ➕(E9-T3)  study.md ➕(E9-T3)
├── scripts/ download_models.py ✔  annotate_roi.py ➕(E8-T0)  make_clips.py ➕(E8-T1)
│   ├── seed_junctions.py ➕(E6-T1)  prefetch_routes.py ➕(E6-T2)
│   └── preflight.py ➕(E10-T1)  run_demo.ps1 ➕(E10-T1)
├── tests/ (9 files ✔, more added per task; conftest.py has vtest_video + frame_context_builder fixtures)
└── docs/ data_checklist.md ➕(E8-T1)  demo_script.md ➕(E10)  report_skeleton.md ➕(E10-T3)
    ├── literature_notes.md  dataset_notes.md  outreach_letter_btp.md  future_work.md ➕(E10-T3)
```

---

## §6. Data Plan

### 6.1 Sources & acquisition policy (user decision 2026-07-08)

| Source | Acquisition | Use |
|---|---|---|
| CADP (~1,400 CCTV accident clips) | **User checklist** (`docs/data_checklist.md`) — hosting/registration varies; E8-T1 verifies current URLs and writes exact steps | Primary positives |
| UCF-Crime `RoadAccidents` | User checklist (crcv.ucf.edu hosts; large download) | Secondary positives |
| CCD (CarCrashDataset, github.com/Cogito2012/CarCrashDataset) | Scriptable if direct links live; else checklist | Secondary |
| DoTA (github.com/MoonBlvd/Detection-of-Traffic-Anomaly) | Checklist | False-alarm tuning |
| Long-form public traffic-cam footage (≥1 h continuous) | Checklist item: user approves/provides a source; suggested search: "traffic intersection live cam archive", "4K road intersection footage long" | Near-miss study (E9-T3) + negatives |
| Occluded rider-down demo clip | **Placeholder now**: best available public clip (or composited crop) proves the pipeline at GATE-A; user stages the ideal clip later — swap = edit `configs/cameras/junction_cam.yaml: source_video` + manifest row only | The demo centerpiece |
| Staged clips (user-filmed, later) | User, clearly labeled "staged" everywhere | Demo + rider-down eval |
| IDD (India Driving Dataset) | Checklist (academic registration) — **only** for stretch E10-T4 | Fine-tuning |

### 6.2 Manifest — single source of truth for eval

`data/manifests/eval_manifest.csv`, header exactly:
```
clip_path,scenario_type,gt_label,gt_event_time_s,camera_config,notes
```
`gt_label` 1/0; `gt_event_time_s` blank for negatives; `scenario_type` ∈ {city_collision, city_riderdown_occluded, city_crowd_only, city_negative, highway_stationary, highway_negative} (extend freely; `*_occluded` suffix is meaningful to E9-T1's occlusion-robustness metric).

### 6.3 Processing conventions

`data/raw/` = untouched downloads. `data/processed/` = normalized by `scripts/make_clips.py` (E8-T1): 1280×720, 25 fps, H.264 crf 23, `-movflags +faststart`, naming `{source}_{index:04d}.mp4`. `data/clips/{incident_id}/` = engine-written evidence (never committed).

### 6.4 Ethics

Blur faces/plates on anything self-recorded before presenting. Staged clips labeled staged in manifest, report, and narration. Public dataset clips used under their academic terms; YouTube-sourced clips are demo texture only, never redistributed. Near-miss study labeled as non-Bengaluru public footage (user decision).

---

## §7. Detection Engine Design

### 7.1 Pipeline per processed frame (target state after E4-T5)

```
VideoSource (wall-clock paced, frame-skipped to target_fps)            [✔ built]
 → Detector.track() : YOLO11 + ByteTrack, class-filtered               [✔ built]
 → TrackHistoryBuilder.update() → FrameContext                         [✔ built]
 → EvidenceBuffer.push(frame)                                          [E4-T3]
 → for each signal: signal.set_current_frame_image(frame.image)        [hook exists]
 → results = {s.name: s.update(ctx) for s in signals}                  [signals ✔]
 → candidate = fusion.update(ctx, results)                             [E4-T1]
 → if candidate: severity.assess() → EvidenceBuffer.start_capture()    [E4-T2/T3]
 → on capture complete: emitter.emit(payload)  (unless --headless)     [E4-T4]
```

### 7.2 As-built components (do not rewrite)

- **`video_source.py`** — `VideoSource(path, target_fps=10.0, speed_factor=1.0)`, yields `Frame(index, timestamp_s, image)` paced to source FPS / speed_factor, skipping to hit target_fps. `timestamp_s` is video time (used everywhere as the engine clock).
- **`detector.py`** — `Detector(weights="models/yolo11s.pt", imgsz=960, conf=0.30, iou=0.5, classes=(person,bicycle,car,motorcycle,bus,truck), device=auto)`, `.track(frame) -> list[Detection(track_id, cls, conf, bbox)]` via `model.track(persist=True, tracker="bytetrack.yaml")`.
- **`tracker_ctx.py`** — `TrackHistoryBuilder(smoothing_window=5).update(frame_index, timestamp_s, detections) -> FrameContext(frame_index, timestamp_s, tracks: dict[int, TrackState])`; `TrackState(track_id, cls, bbox, centroid, velocity px/frame smoothed, bbox_aspect w/h, age_frames)`.
- **`signals/base.py`** — `Signal.update(ctx) -> SignalResult(score 0..1, reasons: list[str], fired_track_ids: list[int])`; `set_current_frame_image(image)` is a base-class no-op hook (only the pose-confirmed rider-down subclass uses it).
- **Signal modules** — all five built and unit-tested against synthetic `frame_context_builder` fixtures. Current tunables are module constants; **E4-T0 converts them to constructor kwargs** (defaults unchanged) so YAML can override:
  - `collision.py`: velocity_drop_threshold 15.0 px/frame over 0.5 s window; near-contact = centroid dist < sum of bbox half-diagonals (or IoU>0); pending impact confirmed when an involved track stays < 3 px/s for ≥ 3 s (pending expiry 15 s — see deviation log); scores 0.6 → 0.95.
  - `rider_down.py`: person aspect > 1.3 sustained ≥ 2 s + immobile (< 3 px/s) + within 1.5× diagonal of a motorcycle/bicycle whose **stored impact-event timestamp** (velocity drop > 15 px/frame or aspect change > 0.5) falls within 3 s of the fall onset; score 0.85. `PoseConfirmedRiderDownSignal` (E3-T3) boosts to 0.95 when torso vector > 60° from vertical (yolo11s-pose on the person crop, every 3rd processed frame, injectable `pose_checker` for tests).
  - `crowd.py`: DBSCAN(eps 40 px, min_samples 4) on person centroids inside road ROI minus exclusion zones; membership observation recorded **every frame** (empty set when no cluster — see deviation log); fires when largest cluster gains ≥ 4 members within 8 s (score 0.5), boosted to 0.8 when new members' velocity vectors converge on the cluster centroid (mean cos-sim > 0.5).
  - `flow.py`: count-line segment-intersection crossings per 10 s bin per approach; collapse = closed bin < 30% of rolling median (last ≤ 29 closed bins) for ≥ 2 consecutive bins; score 0.4 (supporting signal — never fires alone under city weights).
  - `stationary.py`: vehicle centroid inside `live_lane` polygon at < 3 px/s for ≥ 8 s; score ramps 0.5 → 0.9 at 20 s. Constructor takes `live_lane_polygon`; `None` = whole frame (used by the vtest test config).

### 7.3 Config system (E4-T0) — the contract

**`services/detection/config.py`:**
```python
@dataclass DetectorParams: weights, imgsz, conf, iou, classes(list[str]), device("auto")
@dataclass ProcessingParams: target_fps, speed_factor
@dataclass FusionParams: weights dict[str,float], candidate_threshold float,
                         override_rules list[{signal, min_score}], cooldown_seconds float,
                         cooldown_grid tuple[int,int]
@dataclass CameraLocation: lat, lon, label
@dataclass CameraConfig: camera_id, mode, source_video, location: CameraLocation,
                         rois: dict[str, list[[x,y]]],           # keys: road | live_lane
                         exclusion_zones: list[{name, polygon}],
                         count_lines: dict[str, ((x,y),(x,y))],
                         overrides: dict (deep-merged over mode config)
@dataclass EngineConfig: camera: CameraConfig, detector: DetectorParams,
                         processing: ProcessingParams, fusion: FusionParams,
                         signals: dict[str, dict]                # per-signal param dicts, post-merge

def load_engine_config(camera_yaml_path) -> EngineConfig
```
Loader: read camera YAML → read `configs/modes/{mode}.yaml` → deep-merge camera `overrides` onto the mode dict (dict-recursive; camera wins) → build dataclasses. Raise `ValueError` naming the missing key on any absent required field (camera_id, mode, source_video, location).

**`configs/modes/city.yaml` (literal file contents):**
```yaml
detector: {weights: models/yolo11s.pt, imgsz: 960, conf: 0.30, iou: 0.5,
           classes: [person, bicycle, car, motorcycle, bus, truck], device: auto}
processing: {target_fps: 10, speed_factor: 1.0}
signals:
  collision: {velocity_drop_threshold: 15.0, velocity_window_s: 0.5,
              stationary_speed_threshold: 3.0, stationary_duration_s: 3.0,
              pending_expiry_s: 15.0, initial_score: 0.6, confirmed_score: 0.95}
  rider_down: {aspect_lying_threshold: 1.3, sustained_duration_s: 2.0, proximity_multiplier: 1.5,
               vehicle_velocity_drop_threshold: 15.0, vehicle_aspect_change_threshold: 0.5,
               person_speed_threshold: 3.0, event_correlation_window_s: 3.0, primary_score: 0.85,
               pose: {enabled: true, weights: models/yolo11s-pose.pt,
                      check_every_n_frames: 3, lying_angle_deg: 60.0, confirmed_score: 0.95}}
  crowd: {eps_px: 40.0, min_samples: 4, formation_window_s: 8.0, formation_growth_threshold: 4,
          convergence_cos_threshold: 0.5, formation_only_score: 0.5, confirmed_score: 0.8}
  flow: {bin_duration_s: 10.0, rolling_window_bins: 30, collapse_ratio: 0.3,
         min_consecutive_low_bins: 2, fire_score: 0.4}
fusion:
  weights: {collision: 0.35, rider_down: 0.30, crowd: 0.20, flow: 0.15}
  candidate_threshold: 0.5
  override_rules: [{signal: collision, min_score: 0.9}, {signal: rider_down, min_score: 0.85}]
  cooldown_seconds: 60
  cooldown_grid: [4, 4]
```
**`configs/modes/highway.yaml`:** same detector/processing blocks; `signals:` has `stationary: {speed_threshold: 3.0, min_duration_s: 8.0, ramp_full_duration_s: 20.0, initial_score: 0.5, max_score: 0.9}`, plus the same `collision` and `flow` blocks; `fusion: weights {stationary: 0.5, collision: 0.3, flow: 0.2}, candidate_threshold 0.5, override_rules [{signal: collision, min_score: 0.9}, {signal: stationary, min_score: 0.85}], cooldown 60, grid [4,4]`. *(The stationary override lets a long-stalled vehicle fire alone: weighted 0.9×0.5=0.45 < 0.5 otherwise — this override is required for scenario 2 to work.)*

**`services/detection/signal_factory.py`:** `build_signals(cfg: EngineConfig) -> list[Signal]` — for each key under `cfg.signals`: collision→`CollisionSignal(**params)`; flow→`FlowSignal(count_lines=cfg.camera.count_lines, **params)`; stationary→`StationarySignal(live_lane_polygon=cfg.camera.rois.get("live_lane"), **params)`; crowd→`CrowdSignal(road_polygon=cfg.camera.rois.get("road"), exclusion_zones=[z polygons], **params)`; rider_down→`PoseConfirmedRiderDownSignal(...)` if `pose.enabled` else `RiderDownSignal(**params)`. Signals whose key is absent are not built. Unknown key → ValueError.

### 7.4 Fusion (E4-T1) — the contract

`services/detection/fusion.py`, class `FusionEngine(params: FusionParams)`:
- `configure_frame_size(w, h)` — called by the engine on the first frame.
- `update(ctx, results: dict[str, SignalResult]) -> IncidentCandidate | None`:
  1. `weighted = Σ params.weights[name] × results[name].score` over names present in weights.
  2. Fire if `weighted ≥ candidate_threshold` **or** any override rule satisfied (`results[rule.signal].score ≥ rule.min_score`).
  3. Trigger point = mean centroid of all `fired_track_ids` still present in `ctx.tracks` (fallback: frame center). Cell = `(min(gx-1, int(x/w*gx)), min(gy-1, int(y/h*gy)))`.
  4. Cooldown: if the same cell fired within `cooldown_seconds` (video time), return None. Else record `(cell, ts)` and return the candidate.
- `IncidentCandidate` dataclass (defined in fusion.py): `incident_id` (minted here: `inc_{UTC now:%Y%m%d%H%M%S}_{seq:03d}`), `camera_id`, `detected_ts` (video s), `detected_at` (UTC ISO8601 `...Z`), `signals: dict[str,float]` (all results' scores, fired or not), `reasons: list[str]` (concatenated from all results with score>0), `fired_track_ids`, `trigger_cell`, and mutable `severity`/`severity_reasons` (filled by E4-T2) and `evidence_clip_path`/`evidence_snapshot_path` (filled by E4-T3).

### 7.5 Severity (E4-T2) — the contract

`services/detection/severity.py`, pure function `assess(results: dict[str, SignalResult], ctx: FrameContext) -> tuple[str, list[str]]`:
- Let `collision_ids` = fired_track_ids of `results["collision"]` if present; involved-vehicle-count = distinct ids in collision_ids whose `ctx.tracks[id].cls ∈ {car,truck,bus,motorcycle,bicycle}`; pedestrian-hit = any id in collision_ids with cls == "person".
- **HIGH** if `results["rider_down"].score ≥ 0.85` OR pedestrian-hit OR involved-vehicle-count ≥ 3. **MEDIUM** if involved-vehicle-count == 2 AND `results["flow"].score > 0`. Highway: **HIGH** if `stationary ≥ 0.85` AND `collision ≥ 0.6`; **MEDIUM** if stationary alone ≥ 0.85. **LOW** otherwise.
- Reasons: one string per rule that matched, e.g. `"severity HIGH: rider down (0.95)"`. Tracks that already left `ctx.tracks` are simply not counted (acceptable).

### 7.6 Evidence (E4-T3) — the contract

`services/detection/evidence.py`, class `EvidenceBuffer(target_fps, pre_seconds=10, post_seconds=5, out_root="data/clips")`:
- `push(frame: Frame)` every processed frame (deque maxlen = target_fps × pre_seconds).
- `start_capture(candidate, ctx)` → snapshot immediately: trigger frame annotated by the existing `engine.draw_debug_overlay(image, ctx)` plus candidate reasons drawn as text lines bottom-left → `data/clips/{incident_id}/snapshot.jpg`. Then keep collecting `post_seconds` of pushed frames; when complete, write pre+post frames via `cv2.VideoWriter` (mp4v, target_fps) to `raw.mp4`, then if `shutil.which("ffmpeg")`: `ffmpeg -y -i raw.mp4 -c:v libx264 -pix_fmt yuv420p -movflags +faststart evidence.mp4` and delete raw.mp4; else rename raw.mp4 → evidence.mp4 and print a warning (browser playback may fail without H.264 — install ffmpeg).
- `tick(frame)` returns list of completed captures `[(candidate, clip_path, snapshot_path)]` so the engine emits only after the clip exists. Multiple concurrent captures allowed (rare; supported by keeping a list of active captures).

### 7.7 Emitter (E4-T4) — the contract

`services/detection/emitter.py`, class `Emitter(base_url="http://localhost:8000", queue_path="data/queue/pending_incidents.jsonl", retry_interval_s=5.0)`:
- `emit(payload: dict)`: `httpx.post(f"{base_url}/api/incidents/candidate", json=payload, timeout=3.0)`; any exception or non-2xx → append `json.dumps(payload)` line to queue file (create dirs).
- Daemon thread started in `__init__` (`start_retry_thread=True` param; tests pass False): every retry_interval_s, if queue file non-empty, re-POST each line; rewrite file with only the still-failing lines.
- Payload built by the engine per §8.2.1.

### 7.8 Engine integration (E4-T5) — the contract

Rewrite `services/detection/engine.py` around `run(camera_yaml, headless=False, debug_overlay=False, speed_factor=None, max_frames=None, api_base_url="http://localhost:8000") -> list[IncidentCandidate]`:
1. `cfg = load_engine_config(camera_yaml)`; CLI `--speed-factor` overrides cfg.
2. Build: `Detector(**detector params)` (device "auto" → cuda if available), `TrackHistoryBuilder()`, `signals = build_signals(cfg)`, `FusionEngine(cfg.fusion)`, `severity`, `EvidenceBuffer(cfg.processing.target_fps)`, `Emitter(api_base_url)` unless headless.
3. Loop: per frame — buffer.push → set_current_frame_image on all signals → results → fusion.update (configure_frame_size on first frame) → if candidate: `severity.assess` fills severity fields; `buffer.start_capture(candidate, ctx)`; log one line to stdout. Then `completed = buffer.tick(frame)`; for each completed: fill evidence paths; if not headless → `emitter.emit(build_payload(candidate, cfg))`; append candidate to the return list.
4. `--debug-overlay` keeps writing the annotated video exactly as currently built (reuse `draw_debug_overlay`).
5. End of video: flush any in-progress capture (write with whatever post-frames exist), emit, return.
6. CLI: `python -m services.detection.engine --camera <yaml> [--headless] [--debug-overlay] [--speed-factor N] [--api-base-url URL]`.
7. `build_payload` produces exactly the §8.2.1 JSON (location from cfg.camera.location; mode from cfg.camera.mode).

**Committed test config `configs/cameras/vtest_highway_test.yaml`** (vtest.avi is 768×576; the parked car+truck make `stationary` fire — acceptance needs no new data):
```yaml
camera_id: vtest_highway_test
mode: highway
source_video: tests/fixtures/vtest.avi
location: {lat: 12.9716, lon: 77.5946, label: "vtest synthetic highway"}
rois:
  live_lane: [[0, 0], [768, 0], [768, 576], [0, 576]]
overrides: {}
```

### 7.9 Calibration procedure (used at E8-T2)

1. `python scripts/annotate_roi.py --video <clip> --camera configs/cameras/<name>.yaml` (tool built in E8-T0; key map in that task).
2. `python -m services.detection.engine --camera <yaml> --debug-overlay --headless --speed-factor 10` → watch the annotated output; check ROI alignment and whether velocity/eps thresholds look right at this camera's pixel scale.
3. Adjust the camera YAML's `overrides:` block (never the mode YAML, never code), re-run, iterate; log final values in PROGRESS.md.

---

## §8. Backend API Design (E5)

### 8.1 Endpoints

| Method & Path | Behavior |
|---|---|
| `POST /api/incidents/candidate` | Body §8.2.1. Persist `incidents` row (status PENDING_VERIFICATION) + one `incident_signals` row per signal. Broadcast `incident.new` (§8.2.2). 201 → `{"id": ...}`. Duplicate id → 409. |
| `GET /api/incidents` | All incidents, newest first, each shaped like §8.2.2 payload (+ `dispatch` object if any). |
| `GET /api/incidents/{id}` | One incident or 404. |
| `POST /api/incidents/{id}/verify` | Body `{"decision": "confirm"\|"reject"}`. Only valid from PENDING_VERIFICATION (else 409). reject → REJECTED + broadcast `incident.updated`. confirm → CONFIRMED + broadcast; then `sim.ambulance.dispatch_incident(incident)` (E5-T4 ships a stub that only logs; E6-T3 replaces it) → DISPATCHED + broadcast with embedded dispatch. |
| `GET /api/hospitals`, `GET /api/ambulances` | Seeded rows as JSON lists. |
| `GET /api/metrics/summary` | Latest `eval_runs` row's parsed summary; `{"status": "no_runs"}` if none (real content lands in E9-T2). |
| `GET /tiles/{z}/{x}/{y}.png` | Cache-through OSM proxy (§4). Serve from `data/tile_cache` if present; else fetch (UA header), save, serve. Upstream failure + no cache → 502. |
| Static mounts | `/media` → `data/clips`; `/scenario_media` → `data/processed`. Starlette StaticFiles (supports range requests → video seeking works). |
| `WS /ws` | Broadcast-only hub; server ignores inbound messages. |

CORS: `CORSMiddleware(allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])`.
DB: `sqlite:///data/sanjeevani.db` (env `SANJEEVANI_DB_PATH` overrides; tests set it to a tmp path). Startup: `Base.metadata.create_all` + `seed.load_seed_data()` (idempotent: inserts only when the table is empty; missing seed JSON → log warning, continue — lets E5 run before E6-T1 creates the files).

### 8.2 Canonical payloads (Pydantic in `services/api/schemas.py`; TS mirror in `apps/dashboard/src/types/events.ts` — change both together)

**8.2.1 Candidate submission (engine → API):**
```json
{"id": "inc_20260708101530_001", "camera_id": "junction_cam", "mode": "city",
 "severity": "HIGH", "severity_reasons": ["severity HIGH: rider down (0.95)"],
 "signals": {"collision": 0.2, "rider_down": 0.95, "crowd": 0.8, "flow": 0.4},
 "reasons": ["rider_down: person 2 aspect 3.20 sustained 2.4s, near vehicle 1 impact signature at t=8.1s, pose_confirmed_lying",
             "crowd: cluster grew by 5 members within 8s"],
 "location": {"lat": 12.9730, "lon": 77.6194, "label": "Trinity Circle"},
 "evidence": {"clip_path": "data/clips/inc_20260708101530_001/evidence.mp4",
              "snapshot_path": "data/clips/inc_20260708101530_001/snapshot.jpg"},
 "detected_at": "2026-07-08T10:15:30.100Z"}
```
**8.2.2 WS envelope** `{"type": ..., "ts": "<UTC ISO8601Z>", "payload": ...}`. Types:
- `incident.new` — payload = 8.2.1 fields with `status: "PENDING_VERIFICATION"` added and evidence paths converted to URLs: `{"clip_url": "/media/inc_.../evidence.mp4", "snapshot_url": "/media/inc_.../snapshot.jpg"}`.
- `incident.updated` — `{"id", "status"}` plus, when status=="DISPATCHED": `"dispatch": {"dispatch_id", "ambulance_id", "hospital_id", "hospital_name", "eta_seconds", "route": [[lon,lat], ...]}` (route = full GeoJSON LineString coordinates so the dashboard can draw it with no extra fetch).
- `ambulance.position` — `{"dispatch_id", "ambulance_id", "lat", "lon", "heading_deg", "state", "eta_seconds"}`.
- `corridor.updated` — `{"dispatch_id", "junction_id", "junction_name", "signal_state": "GREEN"|"DEFAULT"}`.
- `hospital.alert` — `{"dispatch_id", "hospital_id", "hospital_name", "severity", "incident_type", "eta_seconds"}` (`incident_type` = "rider_down" if that signal ≥0.85 in the incident's signals, else "collision" if ≥0.6, else "stationary_vehicle" if ≥0.85, else "unspecified").

### 8.3 SQLite schema (`services/api/models.py`)

- `incidents`: id PK str, camera_id, mode, status, severity, severity_reasons JSON-text, signals JSON-text, reasons JSON-text, lat, lon, location_label, evidence_clip_path, evidence_snapshot_path, detected_at, verified_at nullable, verify_decision nullable.
- `incident_signals`: id PK autoint, incident_id FK, signal_name, score. (Denormalized copy for per-signal SQL queries; the JSON on incidents is what the API serves.)
- `dispatches`: id PK str (`disp_{seq:04d}`), incident_id FK, ambulance_id FK, hospital_id FK, route_to_scene_geojson text, route_to_hospital_geojson text, state, eta_seconds_initial, created_at, arrived_scene_at, departed_scene_at, arrived_hospital_at (nullable timestamps).
- `ambulances`: id PK str, name, home_lat, home_lon, status IDLE|BUSY, current_lat, current_lon.
- `hospitals`: id PK str, name, lat, lon, trauma_level int (1 best / 2 general).
- `corridor_junctions`: id PK str, name, lat, lon.
- `eval_runs`: id PK autoint, run_at, manifest_path, results_json text.

### 8.4 WS hub (`services/api/ws.py`)

`ConnectionManager`: `connect(ws)` (accept+track), `disconnect(ws)`, `async broadcast(type_: str, payload: dict)` → json.dumps envelope with `ts=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")`, send to all, dropping dead sockets. Module-level singleton `manager`. The `/ws` endpoint loops `receive_text()` and discards (keeps the connection alive), removing on `WebSocketDisconnect`.

---

## §9. Simulation Design (E6)

### 9.1 Seed data (E6-T1) — pinned values (coords approximate; fine for simulation, noted as such in the report)

`data/seed/hospitals.json`:
```json
[{"id":"hosp_01","name":"NIMHANS","lat":12.9430,"lon":77.5960,"trauma_level":1},
 {"id":"hosp_02","name":"St. John's Medical College Hospital","lat":12.9293,"lon":77.6198,"trauma_level":1},
 {"id":"hosp_03","name":"Victoria Hospital","lat":12.9628,"lon":77.5750,"trauma_level":1},
 {"id":"hosp_04","name":"Bowring & Lady Curzon Hospital","lat":12.9857,"lon":77.6057,"trauma_level":2},
 {"id":"hosp_05","name":"Manipal Hospital Old Airport Road","lat":12.9592,"lon":77.6480,"trauma_level":1},
 {"id":"hosp_06","name":"Fortis Hospital Bannerghatta Road","lat":12.8909,"lon":77.5970,"trauma_level":2},
 {"id":"hosp_07","name":"Sparsh Hospital Infantry Road","lat":12.9832,"lon":77.6006,"trauma_level":2},
 {"id":"hosp_08","name":"MS Ramaiah Memorial Hospital","lat":13.0311,"lon":77.5650,"trauma_level":2}]
```
`data/seed/ambulances.json`: amb_01@NIMHANS, amb_02@St. John's, amb_03@Victoria, amb_04@Manipal OAR, amb_05@Ramaiah (same coords as their hospitals; fields `id, name ("Ambulance N"), home_lat, home_lon`).

**Demo incident locations (fixed):** scenario 1 = Trinity Circle `12.9730, 77.6194`; scenario 2 = Hebbal flyover approach NH-44 `13.0358, 77.5970`. These lat/lons go in the two camera YAMLs (E8-T2) and drive route prefetch.

`scripts/seed_junctions.py`: Overpass POST to `https://overpass-api.de/api/interpreter` with `[out:json][timeout:60]; node["highway"="traffic_signals"](12.88,77.54,13.04,77.66); out;` → keep ≤ 40 nodes evenly sampled → `junctions.json` `[{"id":"jct_001","name":(tags.name or "Signal jct_001"),"lat":...,"lon":...}]`. **Fallback if Overpass fails:** commit this hand-curated list of 20 real junctions (approx coords): Trinity Circle 12.9730,77.6194; Domlur 12.9609,77.6387; Ulsoor/Kensington 12.9790,77.6210; Richmond Circle 12.9611,77.5950; Hudson Circle 12.9660,77.5880; Town Hall 12.9645,77.5855; Mysore Bank Circle 12.9689,77.5800; Anil Kumble Circle 12.9757,77.6070; Cubbon Park/Minsk Sq 12.9800,77.5970; Chalukya Circle 12.9846,77.5900; Windsor Manor 12.9910,77.5860; Mekhri Circle 13.0060,77.5760; Sanjaynagar 13.0230,77.5700; Hebbal 13.0358,77.5920; Cauvery Junction 13.0130,77.5800; Shivananda Circle 12.9855,77.5790; Majestic/KBS 12.9767,77.5710; Corporation Circle 12.9645,77.5900; Residency-Brigade 12.9720,77.6070; MG-Brigade 12.9752,77.6060.

### 9.2 Routing (E6-T2)

`services/api/sim/geo.py`: `haversine_m(lat1,lon1,lat2,lon2)`; `polyline_cumdist(coords) -> list[float]` (coords are `[lon,lat]` GeoJSON order — **be careful**); `point_at_distance(coords, cumdist, d) -> (lat, lon, heading_deg)` (linear interpolation within the segment; heading = atan2 east/north bearing); `project_distance(coords, cumdist, lat, lon) -> (route_dist_m, offset_m)` (nearest-vertex approximation is acceptable: distance to nearest vertex + that vertex's cumdist).

`services/api/sim/routing.py`: `get_route(from_lat, from_lon, to_lat, to_lon) -> dict {"coordinates": [[lon,lat],...], "distance_m": float}`. Try OSRM (2 s timeout); on any failure load `data/routes/{key}.geojson` where key matches endpoints rounded to 4 dp against the known seed/demo points (`{from_id}__{to_id}`, ids from a registry of ambulance homes, scenario locations, hospitals); no cache match → raise RuntimeError (dispatch aborts with a logged error; incident stays CONFIRMED).

`scripts/prefetch_routes.py`: fetch + commit all pairs — every ambulance home → each of the 2 scenario locations (10), each scenario location → every hospital (16) = 26 files, plus prints a summary table. Re-runnable (skips existing).

### 9.3 Ambulance mover (E6-T3)

`services/api/sim/ambulance.py`:
- `dispatch_incident(incident) -> dispatch dict`: nearest IDLE ambulance (haversine from current position); hospital = `hospital.select_hospital(incident)`; route amb→scene via routing; create `dispatches` row (state TO_SCENE, eta_seconds_initial = distance_m / (35/3.6)); mark ambulance BUSY; `asyncio.create_task(run_dispatch(dispatch_id, tick_interval_s=1.0))`; return the embedded-dispatch dict for the DISPATCHED broadcast (§8.2.2).
- `run_dispatch`: walk the polyline by cumulative distance; speed 35 km/h × **1.4 when the segment ahead has a GREEN corridor junction within 500 m** (ask corridor module); every tick broadcast `ambulance.position` (eta = remaining_m / current speed); arrival = within 15 m of route end. States: TO_SCENE → AT_SCENE (hold 45 s; fire `hospital.alert` once on entry) → TO_HOSPITAL (new route scene→hospital; corridor set recomputed) → ARRIVED → incident status RESOLVED + broadcast `incident.updated`; ambulance status IDLE, current position = hospital. `tick_interval_s` is a parameter so tests run at 0.005 s.

### 9.4 Corridor sequencer (E6-T4)

`services/api/sim/corridor.py`: at dispatch (and again at TO_HOSPITAL), select junctions with `offset_m ≤ 30` from the active route polyline; store each with its `route_dist_m`. On each mover tick with ambulance route-distance `a`: junction j → GREEN when `0 ≤ (j.route_dist_m - a) ≤ 500`; j → DEFAULT when `a > j.route_dist_m` for ≥ 10 s (store pass timestamp). Broadcast `corridor.updated` **only on state change**. Expose `speed_multiplier(a) -> 1.4 if any GREEN junction within [a, a+500] else 1.0`.

### 9.5 Hospital pre-alert (E6-T5)

`services/api/sim/hospital.py`: `select_hospital(incident)`: sort hospitals by haversine from incident; if severity HIGH, prefer the nearest `trauma_level==1` **if** its distance ≤ 1.5 × absolute nearest's distance, else absolute nearest; MEDIUM/LOW → absolute nearest. `fire_prealert(dispatch)` called by the mover on AT_SCENE entry: broadcast `hospital.alert` once (eta from the scene→hospital route distance at 35 km/h).

---

## §10. Dashboard Design (E7) — MINIMAL UI ONLY

**Standing directive:** functional data-wiring only. Semantic HTML + structural Tailwind classes (`flex`, `grid`, `gap-*`, `p-*`, `overflow-*`, `w-*/h-*`) only. **No color classes, no dark theme, no typography choices, no visual design** — that is E10-T5, BLOCKED on user specs. Where state must be visible (severity, signal state), render it as **text** (e.g. `severity: HIGH`, `state: GREEN`), not color.

Shared plumbing (E7-T1):
- `src/types/events.ts` — TS mirrors of §8.2 (Incident, Dispatch, WSMessage union, AmbulancePosition, CorridorUpdate, HospitalAlert).
- `src/store/index.ts` — zustand: `{incidents: Record<string,Incident>, ambulances: Record<string,AmbulancePosition>, corridor: Record<string,'GREEN'|'DEFAULT'>, hospitalAlerts: HospitalAlert[], wsStatus, applyMessage(msg)}` — `applyMessage` is the single reducer for all five WS types (incident.updated merges; DISPATCHED attaches the dispatch object to the incident).
- `src/lib/ws.ts` — `connectWS(onMessage)`: opens `ws://localhost:8000/ws`, reconnect backoff 1s→2s→4s→10s cap, updates wsStatus.
- `src/lib/api.ts` — `API_BASE = "http://localhost:8000"`; `fetchIncidents()`, `verifyIncident(id, decision)`, `fetchMetricsSummary()`.
- `src/main.tsx` — BrowserRouter, routes `/control /dispatch /hospital /metrics`, store hydrated by `fetchIncidents()` on mount + WS thereafter.

Views (each its own task, §13): Control = `FeedGrid` (`<video autoPlay muted loop>` tags for both scenario files served from `/scenario_media/...`, filenames passed as a prop array) + `IncidentFeed` (cards: id, camera, severity text, first reason, status) + `IncidentDetail` with `WhyPanel` (per-signal `<progress max=1 value=score>` + reasons list) + `VerifyModal` (evidence `<video controls src={clip_url}>`, Confirm/Reject buttons → `verifyIncident`). Dispatch = MapLibre map (raster source `${API_BASE}/tiles/{z}/{x}/{y}.png`, attribution "© OpenStreetMap contributors", center `[77.60, 12.97]` zoom 12) + route GeoJSON line layer + ambulance marker (tween between ticks with requestAnimationFrame over 1 s) + corridor junction circle layer (label = state text) + incident/hospital markers + `Stopwatch` (starts on incident.new, freezes on DISPATCHED, shows seconds) + `EtaBanner`. Hospital = list of alert cards (hospital name, severity text, incident type, live ETA countdown via setInterval). Metrics = tables from `/api/metrics/summary`.

Acceptance for every E7 task = observable behavior (with API running and a canned candidate POSTed via curl) **plus** `npx tsc --noEmit` and `npx vite build` both passing.

---

## §11. Evaluation Harness (E9-T1/T2)

`eval/run_eval.py` CLI: `--manifest data/manifests/eval_manifest.csv [--speed-factor 30]`:
1. Per row: `run(camera_config, headless=True, speed_factor=...)` → candidates.
2. Per-clip record: `{clip, scenario_type, gt_label, predicted (any candidate), first_fire_ts, latency_s (first_fire_ts − gt_event_time_s, positives only), signals (of first candidate), crowd_assisted (signals.get("crowd",0) ≥ 0.5)}`.
3. Summary: `tpr` (predicted positives / positives), `far` (predicted negatives / negatives), `mean_latency_by_scenario_type`, split metrics for crowd-assisted vs direct-only detections, `occlusion_robustness` = count of `*_occluded` rows where crowd ≥ 0.5 **and** collision < 0.9 (the override threshold), `crash_to_dispatch_s: null` (filled manually after a timed live-loop rehearsal; honest label "simulated, human-in-loop").
4. Write `eval/results/{run_id}.json` (run_id = UTC timestamp) + print a markdown table; insert an `eval_runs` row (E9-T2) so `GET /api/metrics/summary` serves it.

`eval/metrics.py` holds the pure functions (unit-tested with a hand-built records list).

## §12. Near-Miss Mini-Study (E9-T3, public footage per user decision)

`eval/near_miss/conflicts.py` CLI: `--video <file> --camera <yaml> [--grid 20] [--window-s 1.5] [--dedupe-s 5]`:
- Track via existing Detector+TrackHistoryBuilder (headless, high speed_factor). Grid = 20×20 over the road ROI bbox. Record `(cell, ts, track_id, cls, speed)` per frame per track (inside ROI only).
- Conflict = two **different** tracks occupying the same cell within `window_s`, at least one with speed > 5 px/s; deduplicate the same track pair within `dedupe_s`. Movement-type pairing from the two classes (pedestrian–vehicle / two-wheeler–vehicle / vehicle–vehicle).
- Outputs: `eval/near_miss/results/{video_stem}_conflicts.csv`, conflicts-per-hour table grouped by hour bucket and pairing, `heatmap.png` (matplotlib hexbin of conflict points over a mid-video frame), and `study.md` filled from a template with an explicit "public non-Bengaluru footage" honesty note.

---

## §13. Build Order — Remaining Epics & Tasks

*(E0, E1, E2, E3-T1, E3-T2 are complete — see PROGRESS.md. Work starts at E3-T3.)*

### E3 — Signals (Novel), remaining

**E3-T3 (revised). Pose confirmation, stub-injected.**
- Goal: finish + test the already-written `PoseConfirmedRiderDownSignal`. The occluded-clip gate formerly here **moves to E8-T3 (GATE-A)** because the clip doesn't exist yet.
- Files: `services/detection/signals/rider_down.py` (already modified, uncommitted), `tests/test_signals_rider_down.py` (extend).
- Steps: review the in-flight code; add tests: (a) reuse the firing fixture from E3-T2, construct `PoseConfirmedRiderDownSignal(pose_checker=lambda crop: True, check_every_n_frames=1)`, call `set_current_frame_image(np.zeros((600,900,3),np.uint8))` before each update → max score ≥ 0.95 and some reason contains `pose_confirmed_lying`; (b) same with `pose_checker=lambda crop: False` → max score == 0.85 exactly; (c) real-model smoke: build `_default_pose_checker()`, run `Detector` on the first vtest frame, crop the first person bbox (+10 px padding, clamped), assert the checker returns `False` (upright pedestrian) without raising.
- Acceptance: all rider-down tests + full suite pass. Commit (this finally commits the in-flight file), push, tick.

### E4 — Fusion + Evidence + Engine wiring

**E4-T0. Config system.** Files: `services/detection/config.py`, `services/detection/signal_factory.py`, `configs/modes/city.yaml`, `configs/modes/highway.yaml` (§7.3 literal contents), `pytest.ini` (`[pytest]\ntestpaths = tests`), signal constructors gain kwargs (defaults = current constants; existing tests must pass unchanged), `.gitignore` += `data/sanjeevani.db`, `tests/test_config.py`. Steps: write dataclasses + loader + deep-merge; refactor the five signals' `__init__`s; factory per §7.3. Acceptance: `load_engine_config` on a tmp camera YAML (mode city) resolves merged params; an override in the camera YAML wins; `build_signals` returns 4 signals for city / 3 for highway with correct types; full suite passes.

**E4-T1. Fusion.** Files: `services/detection/fusion.py`, `tests/test_fusion.py`. Per §7.4. Tests: weighted-sum fire without overrides; override-only fire (rider_down 0.85, everything else 0); cooldown suppresses same-cell candidate at +30 s and allows at +61 s; different cell not suppressed; candidate carries all signal scores + concatenated reasons; incident_id format regex `^inc_\d{14}_\d{3}$`.

**E4-T2. Severity.** Files: `services/detection/severity.py`, `tests/test_severity.py`. Per §7.5, one test per rule row (5 rules + LOW fallback), building results/ctx via existing fixtures.

**E4-T3. Evidence.** Files: `services/detection/evidence.py`, `tests/test_evidence.py`. Per §7.6. Test: feed 200 synthetic frames (solid color w/ frame index drawn) at target_fps 10, trigger at frame 120, tick through post window → `evidence.mp4` exists, `cv2.VideoCapture` frame count ≈ (10+5)×10 ±10%, `snapshot.jpg` decodes; works with and without ffmpeg on PATH (monkeypatch `shutil.which` → None for the fallback case).

**E4-T4. Emitter.** Files: `services/detection/emitter.py`, `tests/test_emitter.py`. Per §7.7. Test: `Emitter(base_url="http://localhost:1", start_retry_thread=False)` → emit queues to a tmp queue path; then spin `http.server` on a free port recording POSTs, call the retry-flush method directly → queue drains, POST body matches.

**E4-T5. Engine integration.** Files: `services/detection/engine.py` (rewrite per §7.8), `configs/cameras/vtest_highway_test.yaml` (§7.8 literal), `tests/test_engine.py` (extend; keep the overlay test). Acceptance (no new data needed): `python -m services.detection.engine --camera configs/cameras/vtest_highway_test.yaml --headless --speed-factor 20` returns ≥1 candidate with `stationary ≥ 0.85` in signals; `data/clips/<id>/evidence.mp4` + `snapshot.jpg` exist and decode; with `--headless` omitted and no API running, the candidate lands in `data/queue/pending_incidents.jsonl`. Full suite green.

### E5 — API Core

**E5-T1. App + models + CORS + seed-on-startup.** Files: `services/api/{main,db,models,seed}.py`. §8.1/8.3. `db.py` reads `SANJEEVANI_DB_PATH`. Acceptance: `./venv/Scripts/python.exe -m uvicorn services.api.main:app` starts; `sqlite3 data/sanjeevani.db ".tables"` shows all 7 tables; `GET /api/hospitals` returns `[]` (seed files don't exist yet — warning logged, no crash).
**E5-T2. Candidate endpoint.** Files: `services/api/schemas.py`, `services/api/routers/incidents.py`, `tests/test_api_incidents.py` (TestClient + tmp DB via env var). POST §8.2.1 example → 201, row persisted, signals rows created; duplicate → 409; GET list/detail shaped per §8.2.2.
**E5-T3. WS hub.** Files: `services/api/ws.py`, wire broadcast into candidate POST. Test: `client.websocket_connect("/ws")` then POST candidate → receives `incident.new` with correct envelope + media URLs.
**E5-T4. Verify + state machine.** Extend incidents router per §8.1 (dispatch call is a logged stub until E6-T3). Tests: reject path, confirm path (status transitions + broadcasts, 409 on re-verify).
**E5-T5. Media mounts + tile proxy.** Files: `services/api/routers/tiles.py`, mounts in main.py. Test: monkeypatched upstream returns bytes → first GET saves `data/tile_cache/1/2/3.png` (tmp dir via env override or monkeypatched cache root), second GET served with upstream disabled.

### E6 — Simulators

**E6-T1. Seed files + startup load.** Files: `data/seed/{hospitals,ambulances}.json` (§9.1 literal values), `scripts/seed_junctions.py` (+ run it; commit `junctions.json`; fall back to the §9.1 curated list if Overpass fails). Acceptance: fresh DB startup → `GET /api/hospitals` returns 8, `/api/ambulances` 5, junction rows ≥ 20.
**E6-T2. Routing client + prefetch.** Files: `services/api/sim/{geo,routing}.py`, `scripts/prefetch_routes.py`, committed `data/routes/*.geojson` (26 files), `tests/test_sim_geo.py` (haversine known value ±1%, point_at_distance on a 2-segment line, projection). Acceptance: with OSRM reachable `get_route` returns a polyline; with base URL monkeypatched to an invalid host it falls back to the cached file for a demo pair.
**E6-T3. Ambulance mover.** Files: `services/api/sim/ambulance.py`, replace the E5-T4 stub, `tests/test_sim_ambulance.py` (monkeypatched `get_route` → straight 2-point line ~2 km; `tick_interval_s=0.005`; collect broadcasts via a stub manager). Assert: state sequence TO_SCENE→AT_SCENE→TO_HOSPITAL→ARRIVED, ≥ 1 position broadcast per state, final incident RESOLVED, eta monotonically ↓ within a leg. Acceptance additionally live: confirm a real posted candidate → `ambulance.position` messages tick ~1/s over `/ws`.
**E6-T4. Corridor.** Files: `services/api/sim/corridor.py`, hook into mover, `tests/test_sim_corridor.py` (synthetic route through 2 seeded junction coords → GREEN within 500 m, DEFAULT 10 s after pass; broadcast only on change).
**E6-T5. Hospital pre-alert.** Files: `services/api/sim/hospital.py`, hook AT_SCENE, `tests/test_sim_hospital.py` (selection rules incl. the 1.5× trauma-preference bound; exactly one alert per dispatch).

### E7 — Dashboard (minimal UI; acceptance always includes `npx tsc --noEmit` + `npx vite build`)

**E7-T1.** Shell/router/types/store/ws/api helpers (§10 plumbing). Acceptance: 4 routes render headings; WS status text flips to `open` with API up.
**E7-T2.** FeedGrid + IncidentFeed. Acceptance: curl-POST candidate → card appears live with severity text.
**E7-T3.** WhyPanel + VerifyModal. Acceptance: signal `<progress>` bars match posted scores; Confirm updates status text live (API logs the dispatch stub or dispatches if E6 done).
**E7-T4.** Dispatch map + ambulance tween + route line. Acceptance: confirmed incident → marker moves smoothly along drawn route.
**E7-T5.** Corridor circles + EtaBanner + Stopwatch. Acceptance: junction labels flip GREEN→DEFAULT during a run; stopwatch freezes at DISPATCHED.
**E7-T6.** Hospital console with ETA countdown. Acceptance: alert card appears at AT_SCENE moment.
**E7-T7.** Metrics tables from `/api/metrics/summary` (renders `no_runs` state until E9). 

### E8 — Scenario Content **[both gates live here]**

**E8-T0. ROI annotation tool.** Files: `scripts/annotate_roi.py`. OpenCV window on the video's first frame. Keys: left-click = add vertex to current shape; `r` = start `road` polygon; `l` = start `live_lane`; `e` = start an exclusion zone (auto-named `excl_N`); `c` = start a 2-point count line (auto-named `line_N`, prompts rename in console); `n` = close/finish current shape; `u` = undo last vertex; `s` = save (deep-merge into `--camera` YAML, preserving unrelated keys); `q` = quit without saving. Drawn shapes rendered live. Acceptance: annotate vtest.avi into a tmp camera YAML → `load_engine_config` loads it cleanly and polygons match clicked points.
**E8-T1. Dataset acquisition — USER ACTION REQUIRED.** Files: `docs/data_checklist.md`, `scripts/make_clips.py`, `data/manifests/eval_manifest.csv` (grows as data lands). Steps: verify current dataset URLs (web search at execution time), write the checklist (exact URLs, registration notes, what to download, target dirs under `data/raw/<source>/`), incl. the long-form footage item for E9-T3 and the placeholder occluded-clip item; write make_clips.py (ffmpeg normalize per §6.3, `--src data/raw/<source> --out data/processed`); process whatever is scriptable now. **Pause point:** manifest needs ≥ 15 rows spanning ≥ 2 positive scenario types + negatives before E8-T3/E9-T1 can run — tell the user exactly what's missing. Build may continue meanwhile with any task not needing footage.
**E8-T2. Demo camera configs + scenarios.** Files: `configs/cameras/junction_cam.yaml` (mode city, location Trinity Circle 12.9730/77.6194), `configs/cameras/highway_cam.yaml` (mode highway, location Hebbal 13.0358/77.5970), `configs/scenarios/scenario{1,2}.yaml` (`{scenario_id, camera_config, description, expected: {type, gt_event_time_s}}`). Calibrate per §7.9 on the chosen clips (placeholder occluded clip per user decision — swapping later = change `source_video` + manifest row only). Acceptance: debug-overlay runs show aligned ROIs on both cameras.
**E8-T3. Scenario 1 end-to-end — GATE-A (the novelty gate).** Full chain live (engine junction_cam → API → dashboard confirm → dispatch). **GATE-A:** on the occluded(-style) clip, `crowd ≥ 0.5` while `collision < 0.9` (stays below its override), fusion crosses threshold, incident reaches DISPATCHED with one Confirm tap. All tuning via camera YAML `overrides`, logged in PROGRESS.md.
**E8-T4. Scenario 2 end-to-end — GATE-B (the demo gate).** Same for highway_cam (stationary override fires). **GATE-B:** both scenarios run back-to-back matching all 7 beats of §1.5 with no manual intervention beyond starting each engine run + Confirm taps. Record pass/fail notes in PROGRESS.md.

### E9 — Evaluation

**E9-T1. Eval runner.** Files: `eval/run_eval.py`, `eval/metrics.py`, `tests/test_eval_metrics.py` (pure-function tests on hand-built records). Per §11. Acceptance: runs on the manifest (needs E8-T1 data) → results JSON + markdown table.
**E9-T2. Metrics API + dashboard wiring.** eval_runs insert; real `GET /api/metrics/summary`; `/metrics` view shows real numbers.
**E9-T3. Near-miss study (public footage per user decision).** Files: `eval/near_miss/conflicts.py`, `study.md`. Per §12. Footage source = user-approved long-form public recording from the checklist. Acceptance: CSV + heatmap + study.md with conflicts/hour table, honestly labeled.

### E10 — Polish + Demo Insurance

**E10-T1. Runbook.** Files: `scripts/preflight.py` (checks: CUDA available, ports 8000/5173 free, ffmpeg present, `data/routes/` complete for demo pairs, tile cache non-empty, both scenario videos exist), `scripts/run_demo.ps1` (start API, start vite, open 3 browser windows at the routes, print the two engine commands; `-Scenario 1|2` launches the engine for that camera).
**E10-T2. Rehearsal + backup video.** `docs/demo_script.md`: the 7 beats mapped to exact operator actions + failure playbook (§14); rehearse ≥ 5×; record a flawless full run (Win+G Game Bar or OBS; path noted in the doc, file not committed).
**E10-T3. Report skeleton.** `docs/report_skeleton.md` (chapters: intro/problem, related work, architecture, novel signals, simulation design, evaluation incl. E9 numbers, near-miss study, ethics, future work), `docs/future_work.md` (the Describe bucket), fill metrics from E9.
**E10-T4 (stretch, optional).** IDD fine-tuning per original plan — skippable.
**E10-T5. Styling pass — BLOCKED ON USER.** Apply the user's design specs across the dashboard. Do not start without them.

---

## §14. Demo Runbook (target state; finalized in E10)

Pre-flight = `python scripts/preflight.py` (all checks green). Start = `scripts/run_demo.ps1`. Windows: `/control` (operator), `/dispatch` (map), `/hospital`. Sequence = §1.5 beats; only manual actions are launching each scenario's engine run and the two Confirm taps. Failure playbook: API dies → rerun its command (WS auto-reconnects; in-flight dispatch is lost but a fresh candidate works); network dies → invisible (caches); catastrophic → backup video from E10-T2.

## §15. Testing Strategy, Risks, Glossary

**Tests:** signal/fusion/severity/geo/metrics = pure-Python on synthetic fixtures (`frame_context_builder`); detector/engine/pose-smoke = vtest.avi fixture (auto-downloaded); API = TestClient + tmp SQLite (env `SANJEEVANI_DB_PATH`); simulators = monkeypatched routes + near-zero tick intervals + stub broadcast manager; dashboard = `tsc --noEmit` + `vite build` + manual observable checks. Full suite before every commit.

**Key risks:** COCO has no auto-rickshaw class (mapped to car/truck — known limitation, stretch E10-T4 addresses); public OSRM/tile availability (caches mitigate; prefetch early); dataset link rot (checklist verified at E8-T1 execution time); occluded-clip quality (placeholder now, user stages later — GATE-A proves the mechanism either way); scope creep (Describe bucket → docs only).

**Glossary:** ICCC (Integrated Command & Control Centre); golden hour; PET (Post-Encroachment Time); ByteTrack (persistent multi-object tracking); green corridor; DBSCAN; ROI.
