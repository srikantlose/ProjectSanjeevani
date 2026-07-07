# Project Sanjeevani — End-to-End Build Plan

This document is the single source of truth for building Project Sanjeevani. It is written so that an AI coding agent (or a human) with no prior context can open this file, open `PROGRESS.md`, and start building at the first unchecked task — no additional design decisions required. Read this whole file once before writing any code. Then work top-to-bottom through §13.

---

## §1. Project Overview & How To Use This Document

### 1.1 What this project is

Sanjeevani is an AI system that watches traffic camera video, detects probable road accidents within seconds, has a human operator confirm them with one tap, classifies severity, and drives a simulated emergency response: ambulance dispatch on a real Bengaluru map, a green-corridor signal sequence along the route, and a hospital pre-alert. It is a solo final-year academic project. The deliverable is a **working, rehearsed, five-minute live demo** plus a written report — not a production system.

### 1.2 The core loop

**Detect → Verify → Triage → Dispatch → Resolve.**

1. **Detect** — a Python video-analysis engine watches a camera feed (a video file, played back at real-time pace to simulate a live camera) and raises an `IncidentCandidate` when its signal-fusion logic crosses a threshold.
2. **Verify** — a human operator, in the control-room dashboard, sees a short clip and taps Confirm or Reject. This is a deliberate feature (kills false-alarm fatigue), not a shortcut.
3. **Triage** — the engine attaches a severity label (LOW/MEDIUM/HIGH) and human-readable reasons at detection time; the operator sees this immediately.
4. **Dispatch** — on confirm, the backend picks the nearest simulated ambulance, routes it on a real Bengaluru road network, and starts moving it.
5. **Resolve** — signals along the ambulance's route turn green in sequence (green corridor) and the nearest matching hospital gets a pre-alert card with severity and live ETA.

### 1.3 The two novel claims + the prevention chapter

This is what makes the project defensible academically, not a tutorial reproduction. Everything else is supporting infrastructure for these three ideas:

1. **Crowd-as-signal detection.** In Indian traffic, a crowd of bystanders forms around a crash within seconds — often before, or instead of, a clear view of the crash itself. The engine detects sudden pedestrian clustering *on the carriageway* as an independent accident signal. This is what fires when the actual impact is occluded (e.g., hidden behind a bus). It is the single most important thing to get working and to be able to demonstrate — see §7.4 and the Phase/Epic gate in E3.
2. **Rider-down + severity triage.** Most published accident-detection work assumes lane-disciplined cars. India's roads are dominated by two-wheelers, which are the largest fatality category. The engine specifically detects a rider down (not just "a collision happened") and always emits a severity label with reasons, not a bare yes/no.
3. **Near-miss analytics (prevention chapter).** A small observational study on self-recorded junction footage: count near-misses (using a Post-Encroachment-Time proxy) per hour, broken down by time-of-day and movement type. This turns the report from "we built an alarm" into "we measured road-safety risk," and gives the panel a second, independent finding. See §12.

### 1.4 Scope discipline: Build / Simulate / Describe

Every feature belongs to exactly one bucket. Do not blur these. If a new idea comes up while building, it goes into `docs/` (vision/future-work), not into the codebase, unless it is already listed below.

**Build (real, working code, in this repo):**
- Video-based accident detection: direct signals + crowd-as-signal (novelty #1).
- Rider-down detection + severity triage (novelty #2).
- Control-room dashboard: live feed tiles, one-tap verify, incident cards with location/severity/snapshot/"why" panel.

**Simulate (fully functional code, but the real-world actor is mocked):**
- Ambulance dispatch: a simulated ambulance moving on real Bengaluru roads via real routing.
- Green corridor: junction markers on the map flip green in sequence as the ambulance approaches.
- Hospital pre-alert: a console showing severity + live ETA.
- One highway scenario (stationary vehicle in a live lane) proving the same detection brain generalizes to "highway mode."

**Describe (report/docs only — never code):**
- Real 112/108 dispatch integration, live police/ICCC camera feeds, signal-preemption hardware, evidence chain-of-custody / auto-FIR, insurance automation, citizen apps, FASTag fusion, statewide rollout. These live in `docs/` as vision/future-work writing.

### 1.5 The demo storyline (design everything backwards from this)

Everything built must serve this five-minute sequence, run live in three browser windows (`/control`, `/dispatch`, `/hospital`) plus the recorded scenario videos:

1. Junction footage plays. A two-wheeler goes down, partially occluded by a bus.
2. Within seconds, the system flags an incident. The "why" panel shows: crowd clustering detected, flow collapse at the junction (direct collision signal was weak/absent — occlusion).
3. Severity triage appears: "Two-wheeler rider down — HIGH severity."
4. Operator sees a 5-second clip, taps Confirm.
5. Ambulance dispatches on the Bengaluru map; junction signals flip green one by one as it approaches; hospital console lights up with severity + ETA. A stopwatch on screen shows crash-to-dispatch time.
6. Cut to a highway clip: stationary vehicle in a live lane, same engine, highway mode — proves the platform generalizes.
7. Closing slide: measured detection latency, false-alarm rate, occlusion-robustness numbers, simulated crash-to-dispatch time vs. the ~8–15 minute call-based baseline, and an integration roadmap slide (from `docs/`).

A flawless recorded video of this full run is captured early in the polish phase (E10) as insurance — live demo first, video as fallback if anything breaks live.

### 1.6 Instructions for whoever (or whatever) builds this

- **Work one task at a time**, in the exact order given in §13. Each task lists its files, its steps, and an **acceptance check** — a concrete command or observable behavior that proves the task is done. Do not start a task until the previous one's acceptance check passes.
- **Tick the box** for the task in `PROGRESS.md` immediately after its acceptance check passes, and add a one-line note if anything deviated from the plan (e.g., a threshold that had to change).
- **Never hardcode a tunable value.** Every threshold, weight, or parameter mentioned in §7 lives in a YAML config file (see §5, §7.9). If a threshold doesn't work on real footage, change the YAML, not the code, and note the new value + why in `PROGRESS.md`.
- **Do not refactor ahead of the task list.** If task E2-T2 doesn't need a class hierarchy yet, don't build one because a later task might want it. Build what the current task needs.
- **Commit after every passing task** (if using git), with a plain, human-sounding message describing what was built (e.g., "Add collision signal with velocity-drop heuristic"), no AI attribution.
- **When blocked by a missing dataset or external service**, use the fallback named in the relevant section (§6, §9) and note the substitution in `PROGRESS.md` — never silently skip a task's outcome.
- Read the section referenced by a task before starting it — the task list is deliberately terse and points back to the detailed spec sections.

---

## §2. Locked Decisions

These were decided up front and should not be revisited mid-build:

| Decision | Value |
|---|---|
| Compute | Local machine with an NVIDIA CUDA-capable GPU. Train/fine-tune and run inference locally. |
| Detection framework | Ultralytics YOLO11 + built-in ByteTrack tracker. |
| Backend | Python 3.11, FastAPI, SQLite (via SQLAlchemy), asyncio background tasks for simulators. |
| Dashboard | React 18 + Vite + TypeScript + Tailwind CSS + MapLibre GL JS + Zustand for state. |
| Connectivity | Internet available during build and demo; every network dependency (routing, map tiles) has a committed offline fallback so a bad venue Wi-Fi does not sink the demo. |
| OS | Windows 11. All shell commands in this plan are PowerShell; Python venv activated via `venv\Scripts\Activate.ps1`. |
| Package managers | `pip` + `venv` for Python; `npm` for Node (Node 20 LTS). |
| Video/image tooling | OpenCV (`opencv-python`) for frame IO; `ffmpeg` (installed via `winget install Gyan.FFmpeg`) for clip transcoding. |

---

## §3. System Architecture

### 3.1 Processes

Four things run simultaneously during a demo: three server-side processes plus the browser (which itself opens 3 dashboard routes in separate windows/tabs).

```
┌─────────────────────────┐      HTTP POST /api/incidents/candidate      ┌──────────────────────────────┐
│  Detection Engine        │ ───────────────────────────────────────────▶ │   Backend API (FastAPI)       │
│  services/detection       │                                             │   services/api                 │
│                           │                                             │                                │
│  video file (scenario)    │                                             │  SQLite  ── incidents,         │
│    → YOLO11 detect        │                                             │            dispatches,         │
│    → ByteTrack track      │                                             │            ambulances,         │
│    → signal modules       │                                             │            hospitals,          │
│    → fusion + severity    │                                             │            corridor_junctions  │
│    → evidence clip write  │                                             │                                │
└─────────────────────────┘                                             │  WebSocket hub /ws  ───────────┼──▶  Dashboard (React)
                                                                          │                                │      apps/dashboard
                                                                          │  Simulators (asyncio tasks):   │      /control  /dispatch
                                                                          │   - ambulance mover (1 Hz)     │      /hospital  /metrics
                                                                          │   - green corridor sequencer   │
                                                                          │   - hospital pre-alert         │
                                                                          │                                │
                                                                          │  Tile-cache proxy /tiles/**    │
                                                                          │  Static media /media/**        │
                                                                          └──────────────────────────────┘
```

### 3.2 Event flow (one full incident, step by step)

1. Engine's fusion step crosses threshold → engine POSTs `IncidentCandidate` JSON + evidence file paths to `POST /api/incidents/candidate`.
2. API persists an `incidents` row with status `PENDING_VERIFICATION`, persists `incident_signals` rows (per-signal scores/reasons), and pushes a `incident.new` WebSocket message to all connected dashboard clients.
3. Operator opens the incident in `/control`, watches the evidence clip, taps **Confirm**.
4. Dashboard calls `POST /api/incidents/{id}/verify` with `{"decision": "confirm"}`.
5. API sets status `CONFIRMED`, immediately: (a) picks nearest ambulance, (b) requests a route, (c) creates a `dispatches` row, (d) starts the three asyncio simulator tasks for this dispatch, (e) pushes `incident.updated`.
6. Ambulance mover ticks once per second, computing the ambulance's interpolated position along the route polyline, and pushes `ambulance.position`. When it is within 500 m (route-distance) of a corridor junction, the corridor sequencer pushes `corridor.updated` (junction → GREEN); 10 s after the ambulance passes, that junction reverts (another `corridor.updated`).
7. When the ambulance's simulated state reaches `AT_SCENE`, hospital pre-alert fires immediately (it doesn't wait for arrival) — the destination hospital is chosen at dispatch time (step 5) using severity + distance, and its console shows a `hospital.alert` message with live ETA that ticks down as `ambulance.position` updates.
8. Ambulance state machine continues: `TO_SCENE → AT_SCENE (45s dwell) → TO_HOSPITAL → ARRIVED`. On `ARRIVED`, incident status becomes `RESOLVED`.

### 3.3 Incident lifecycle state machine

```
DETECTED → PENDING_VERIFICATION → CONFIRMED → DISPATCHED → EN_ROUTE → AT_SCENE → TO_HOSPITAL → ARRIVED → RESOLVED
                                 ↘ REJECTED
```
`DETECTED` and `PENDING_VERIFICATION` are effectively simultaneous (an incident is created already pending verification); the separate `DETECTED` name exists for the audit log / eval harness which cares about the exact detection timestamp before any human step.

### 3.4 Why this shape

- Splitting engine and API into separate processes means the CV pipeline's frame-rate hiccups never block the WebSocket hub or the dashboard, and it mirrors the real deployment shape (edge box at camera vs. control-room server) described in the vision chapter.
- SQLite is sufficient — single demo machine, no concurrent-writer problem, zero ops overhead.
- Everything the internet could take away (routing, map tiles) is wrapped by the API server with a disk cache, so a rehearsal run makes the demo venue-network-proof.

---

## §4. Tech Stack (with rationale)

### 4.1 Detection engine (Python)

| Package | Purpose | Note |
|---|---|---|
| `ultralytics` | YOLO11 object detection + built-in ByteTrack multi-object tracking | AGPL-3.0 license — acceptable for an academic, non-distributed project. Cite in report. |
| `torch`, `torchvision` | Backing framework for Ultralytics | Install the CUDA build matching the local GPU driver (see E0-T3). |
| `opencv-python` | Video IO, frame drawing, ROI drawing tool | |
| `supervision` | Convenience for zone polygons, annotators, byte-track glue | Optional but saves boilerplate — use its `PolygonZone` for ROI checks. |
| `scikit-learn` | `DBSCAN` for crowd clustering | |
| `numpy`, `scipy` | Numeric plumbing, velocity smoothing | |
| `shapely` | ROI/polygon geometry (point-in-polygon, distances) | |
| `pyyaml` | Config file loading | |
| `httpx` | Engine → API POST calls | |
| `pytest` | Unit tests for signal modules | |

### 4.2 Backend API (Python)

| Package | Purpose |
|---|---|
| `fastapi` | REST + WebSocket server |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy` | ORM over SQLite |
| `pydantic` | Request/response schemas (FastAPI native) |
| `httpx` | Outbound calls to OSRM routing, Overpass, OSM tile server |
| `websockets` | (pulled in by uvicorn[standard], used for the `/ws` hub) |

### 4.3 Dashboard (Node/React)

| Package | Purpose |
|---|---|
| `react`, `react-dom` | UI |
| `react-router-dom` | Routes: `/control`, `/dispatch`, `/hospital`, `/metrics` |
| `vite`, `typescript` | Build tooling |
| `tailwindcss` | Styling |
| `maplibre-gl` | Map rendering (raster tiles, markers, animated polylines) |
| `zustand` | Global store (incidents, ambulance positions, WS connection) |

No charting library — `/metrics` is plain HTML tables and minimal inline SVG bars, kept dependency-free.

### 4.4 Routing & maps

- **Routing:** OSRM's public demo server (`https://router.project-osrm.org/route/v1/driving/...`) as the primary source at build time and during rehearsals. Because a public server cannot be relied on for a live demo, `scripts/prefetch_routes.py` fetches and commits every route the demo actually uses as GeoJSON under `data/routes/`. At runtime, the routing client tries the live OSRM call first (short timeout, e.g. 2 s) and falls back to the cached GeoJSON on any failure. This satisfies "internet OK, offline fallback."
- **Map tiles:** standard OSM raster tiles, but never fetched directly by the browser. The API exposes `GET /tiles/{z}/{x}/{y}.png`, which fetches from `https://tile.openstreetmap.org/{z}/{x}/{y}.png` on first request and caches the PNG to `data/tile_cache/{z}/{x}/{y}.png` forever after. One full rehearsal at the demo zoom/pan range makes the whole demo tile-set locally cached and network-independent thereafter. MapLibre is pointed at `/tiles/{z}/{x}/{y}.png`, never at the public OSM host directly.
- **Junction (traffic signal) coordinates:** fetched once via the Overpass API (`overpass-api.de`) by `scripts/seed_junctions.py`, querying `highway=traffic_signals` nodes within a bounding box around the demo route; the result is committed to `data/seed/junctions.json` and used as the actual runtime source (Overpass is not called during the demo itself — this is a build-time data-collection step, not a runtime dependency).

---

## §5. Repository Layout

Create exactly this structure (folders may be created empty with a `.gitkeep` where no file exists yet):

```
Project Sanjeevani/
├── plan.md
├── PROGRESS.md
├── README.md
├── .gitignore
├── requirements.txt
├── configs/
│   ├── cameras/
│   │   ├── junction_cam.yaml
│   │   └── highway_cam.yaml
│   ├── modes/
│   │   ├── city.yaml
│   │   └── highway.yaml
│   └── scenarios/
│       ├── scenario_junction_riderdown.yaml
│       └── scenario_highway_stationary.yaml
├── data/
│   ├── raw/                  # untouched source footage
│   ├── processed/            # trimmed/normalized clips ready for the engine
│   ├── clips/                # engine-written evidence clips, per incident_id
│   ├── manifests/
│   │   └── eval_manifest.csv
│   ├── routes/                # cached OSRM GeoJSON per demo route
│   ├── tile_cache/             # cached OSM PNG tiles (gitignored, rebuilt by rehearsal)
│   └── seed/
│       ├── hospitals.json
│       ├── junctions.json
│       └── ambulances.json
├── models/                    # downloaded/fine-tuned weights (gitignored)
├── services/
│   ├── detection/
│   │   ├── engine.py
│   │   ├── video_source.py
│   │   ├── detector.py
│   │   ├── tracker_ctx.py
│   │   ├── ring_buffer.py
│   │   ├── fusion.py
│   │   ├── severity.py
│   │   ├── emitter.py
│   │   └── signals/
│   │       ├── base.py
│   │       ├── collision.py
│   │       ├── rider_down.py
│   │       ├── crowd.py
│   │       ├── flow.py
│   │       └── stationary.py
│   └── api/
│       ├── main.py
│       ├── db.py
│       ├── models.py
│       ├── schemas.py
│       ├── ws.py
│       ├── routers/
│       │   ├── incidents.py
│       │   ├── hospitals.py
│       │   ├── ambulances.py
│       │   ├── metrics.py
│       │   └── tiles.py
│       └── sim/
│           ├── ambulance.py
│           ├── corridor.py
│           ├── hospital.py
│           └── routing.py
├── apps/
│   └── dashboard/              # Vite app
│       └── src/
│           ├── views/
│           ├── components/
│           ├── store/
│           ├── lib/
│           └── types/
├── eval/
│   ├── run_eval.py
│   ├── metrics.py
│   └── near_miss/
│       ├── conflicts.py
│       └── study.md
├── scripts/
│   ├── annotate_roi.py
│   ├── prefetch_routes.py
│   ├── seed_junctions.py
│   ├── make_clips.py
│   ├── download_models.py
│   └── run_demo.ps1
├── tests/
│   ├── test_signals_collision.py
│   ├── test_signals_rider_down.py
│   ├── test_signals_crowd.py
│   ├── test_signals_flow.py
│   ├── test_signals_stationary.py
│   ├── test_fusion.py
│   └── test_api_incidents.py
└── docs/
    ├── demo_script.md
    ├── outreach_letter_btp.md
    ├── report_skeleton.md
    ├── literature_notes.md
    ├── dataset_notes.md
    └── future_work.md
```

---

## §6. Data Plan

### 6.1 Datasets (named concretely)

| Dataset | Use | Notes |
|---|---|---|
| **CADP** (Car Accident Detection and Prediction, ~1,400 CCTV accident clips) | Primary positive examples for direct-collision detection and eval | Traffic-camera viewpoint, closest to this project's setting. |
| **UCF-Crime**, `RoadAccidents` class | Secondary positives | Mixed camera quality; use selectively. |
| **CCD (Car Crash Dataset)** | Secondary positives, dashcam angle | Useful for diversity, not primary viewpoint match. |
| **DoTA** (Detection of Traffic Anomalies) | Secondary/negative-space anomalies | Dashcam; useful for false-alarm tuning. |
| **IDD — India Driving Dataset** (IIIT-Hyderabad, free academic registration) | *Optional* fine-tuning source for India-specific classes (auto-rickshaws, two-wheeler riders, animals on road) | Only pursued in the optional stretch epic (E10 stretch); the base YOLO11 COCO classes (person, bicycle, car, motorcycle, bus, truck) are sufficient for the MVP. |
| Self-recorded Bengaluru junction footage | Negatives (ordinary traffic, no accident) + the near-miss study (§12) | Public vantage points only. Blur faces and license plates before anything is presented or published — see §6.4. |
| Staged rider-down clips | Fills the gap where real rider-down footage is scarce | Clearly labeled "staged" in the manifest and in the report; a volunteer safely laying a bicycle/motorcycle down in a controlled, low-traffic setting. |
| Curated Indian CCTV clips (YouTube, news-embedded accident footage) | Qualitative demo texture only, never the primary eval set | Note usage caveats (rights, not for redistribution) in `docs/dataset_notes.md`. |

### 6.2 Manifest format — the single source of truth for evaluation

`data/manifests/eval_manifest.csv`, columns:

```
clip_path,scenario_type,gt_label,gt_event_time_s,camera_config,notes
data/processed/cadp_0231.mp4,city_collision,1,12.4,configs/cameras/junction_cam.yaml,"CADP clip 231, two-vehicle side impact"
data/processed/junction_neg_014.mp4,city_negative,0,,configs/cameras/junction_cam.yaml,"ordinary traffic, no incident"
data/processed/staged_riderdown_02.mp4,city_riderdown_occluded,1,8.1,configs/cameras/junction_cam.yaml,"staged, bus occlusion at impact"
data/processed/highway_stationary_01.mp4,highway_stationary,1,20.0,configs/cameras/highway_cam.yaml,"stalled car in left lane"
```

- `gt_label`: 1 = incident occurs in this clip, 0 = pure negative.
- `gt_event_time_s`: ground-truth time of the incident's actual onset (blank for negatives); used to compute detection latency.
- `scenario_type`: a free-text tag used to group eval results (city_collision, city_riderdown_occluded, city_crowd_only, highway_stationary, city_negative, etc).

### 6.3 Directory conventions

- `data/raw/`: exactly as downloaded/recorded, never edited.
- `data/processed/`: trimmed to relevant window, resized/re-encoded to a consistent format (`scripts/make_clips.py`, e.g. 1280×720, 25fps, H.264) — this is what the engine and eval harness actually read.
- `data/clips/{incident_id}/evidence.mp4` and `snapshot.jpg`: written by the running engine at demo/eval time, not checked in.

### 6.4 Data-collection protocol (self-recorded junction footage)

1. Choose 2–3 busy Bengaluru junctions, record from a public vantage point (footbridge, roadside, parked position) — never trespass or set up on private property.
2. Record in short (10–20 min) sessions across different times of day (to support the near-miss time-of-day breakdown).
3. Immediately after recording, run a face/plate blur pass (a simple approach: run the same YOLO person/vehicle detector, blur the top-third of person boxes and the license-plate region of vehicle boxes) before this footage is ever shown to anyone outside the build process. Keep the unblurred original only in `data/raw/` (never committed, never presented).
4. Log each session in `docs/dataset_notes.md`: location, date, time window, duration, weather.

### 6.5 Ethics note

No footage showing an identifiable real injury/death is to be used in the public demo or report without blurring and without restricting to what is already public-domain accident-dataset footage (CADP/UCF-Crime/CCD/DoTA are established academic datasets used exactly for this purpose). Staged clips must be clearly labeled as staged everywhere they appear (manifest, report, demo narration).

---

## §7. Detection Engine Design

### 7.1 Pipeline overview

Per scenario video, the engine (`services/detection/engine.py`) runs a loop:

```
decode frame (paced at real wall-clock rate to simulate a live feed)
  → skip to hit target processing rate (10 FPS default; configurable)
  → YOLO11 detect + ByteTrack update  (detector.py)
  → build/update FrameContext: per-track position, bbox, class, velocity history (tracker_ctx.py)
  → run each enabled signal module against FrameContext, collect (signal_name, score, reasons) (signals/*.py)
  → fusion.py: weighted combine + override rules + cooldown → maybe produce IncidentCandidate
  → if candidate produced: severity.py assigns severity + reasons; ring_buffer.py writes evidence clip + snapshot
  → emitter.py POSTs candidate + evidence paths to the API (queues locally if the API is unreachable)
```

### 7.2 Real-time pacing

Because the "camera" is really a video file, `video_source.py` must not just rip frames as fast as OpenCV can decode them — it paces frame delivery to the file's own FPS (using `time.sleep` to match wall-clock), so latency measurements (§11) are meaningful and the demo looks like a live feed. A `speed_factor` config value (default 1.0) allows speeding up for iteration during development.

### 7.3 Detector + tracker defaults

All values below are defaults in `configs/modes/city.yaml` / `configs/modes/highway.yaml`, overridable per-camera in `configs/cameras/*.yaml`. Document every pixel/velocity threshold as **camera-calibration-dependent** — see §7.9 calibration procedure.

```yaml
detector:
  weights: models/yolo11s.pt
  imgsz: 960
  conf: 0.30
  iou: 0.5
  classes: [person, bicycle, car, motorcycle, bus, truck]   # COCO class names filtered post-inference
  device: cuda:0
tracker:
  type: bytetrack
  config: bytetrack.yaml     # ships with ultralytics; persist=True across frames
processing:
  target_fps: 10
  speed_factor: 1.0
```

Call pattern (conceptually): `model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.30, iou=0.5, classes=[...])`.

### 7.4 Signal modules

Each signal module implements a common interface (`signals/base.py`):

```python
class Signal:
    name: str
    def update(self, frame_ctx: FrameContext) -> SignalResult:
        """Called once per processed frame. Returns SignalResult(score: float 0..1, reasons: list[str], fired_track_ids: list[int])."""
```

`FrameContext` carries, per active track: `track_id`, `cls`, `bbox`, `centroid`, `velocity` (px/frame, smoothed over last 5 frames), `bbox_aspect` (w/h), `age_frames`, plus the raw frame timestamp and frame index.

**collision** (`signals/collision.py`) — direct impact detection:
- Trigger candidates: any two tracks whose bboxes overlap (IoU > 0) **or** whose centroid distance is less than the sum of their bbox half-diagonals (near-contact, handles fast-approach frames where boxes haven't overlapped yet).
- Require: at least one of the two tracks shows `|Δv| > 15 px/frame` within a 0.5 s window (a sudden speed change — impact signature).
- Confirm: within 3 s after the above, at least one involved track becomes stationary (`speed < 3 px/s`) for ≥ 3 s.
- Score ramps 0.6 (overlap + velocity drop seen) → 0.95 (stationary-confirmed).

**rider_down** (`signals/rider_down.py`) — novelty #2, primary heuristic:
- A `person` track's bbox aspect ratio (w/h) flips from the normal standing range (~0.3–0.6) to **> 1.3** (wide-and-flat = lying down), sustained for ≥ 2 s.
- AND that person's centroid is within 1.5× a nearby `motorcycle`/`bicycle` track's bbox diagonal, and that vehicle track either decelerated sharply (`|Δv| > 15 px/frame`) or its own bbox aspect changed sharply (bike now lying on its side).
- AND the person track's velocity stays near zero (`< 3 px/s`) for the sustained window (rules out a person merely crouching/bending briefly).
- Score: 0.85 on aspect+proximity match alone (this alone is allowed to fire an incident per the fusion override rule, §7.6); pushed toward 0.95 with pose confirmation.
- **Pose confirmation** (secondary, GPU-affordable check): run `yolo11s-pose` on the cropped person bbox every 3rd processed frame while the primary heuristic is active; if the torso keypoint vector (shoulder-midpoint → hip-midpoint) is more than 60° from vertical, add +0.1 to score and add reason `"pose_confirmed_lying"`.

**crowd** (`signals/crowd.py`) — novelty #1, the most important signal in the whole project:
- Take all `person` track centroids currently inside the camera's `road` ROI polygon (from camera YAML), excluding any point inside an `exclusion_zones` polygon (e.g., a bus stop where people normally stand).
- Cluster with `sklearn.cluster.DBSCAN(eps=40, min_samples=4)` (pixel units — calibration-dependent, see §7.9) on the centroid coordinates of the current frame.
- Track cluster size over an 8 s sliding window. Fire when a cluster's member count on the carriageway grows by **≥ 4 people within 8 s** (rate of formation, not just absolute size — an already-large stable crowd, e.g. at a signal waiting to cross, should not fire).
- AND require that the mean walking-direction vector of the newly-added members has cosine similarity **> 0.5** with the vector pointing from each member toward the cluster centroid (people are converging on a point, not just co-located pedestrians walking past each other in parallel).
- Score ramps 0.5 (formation-rate met) → 0.8 (formation-rate + convergence met).
- This is the signal that must fire on the occluded-impact demo clip when `collision` is silent — see the E3 gate.

**flow** (`signals/flow.py`) — traffic-flow collapse, a supporting signal:
- Define virtual count-lines per traffic approach in camera YAML (a line segment; a track "crosses" it when its centroid path intersects the segment between consecutive frames).
- Maintain throughput (crossings) per 10 s bin per approach, and a rolling 5-minute median for that bin's time-of-day (simplify for the MVP: rolling median over the last 30 bins = last 5 minutes, not time-of-day-aware — that refinement is future work).
- Fire when throughput on a normally-active approach drops **below 30% of the rolling median for ≥ 2 consecutive 10 s bins**.
- Score: 0.4 at threshold (this is a supporting signal, never fires alone — see fusion weights).

**stationary** (`signals/stationary.py`) — highway mode's primary signal:
- Any `car`/`truck`/`bus`/`motorcycle` track whose centroid stays inside a `live_lane` ROI polygon with displacement **< 3 px/s sustained for ≥ 8 s**.
- Score ramps 0.5 (8 s) → 0.9 (20+ s, clearly abandoned/stalled rather than a momentary traffic-jam stop — cross-check against the `flow` signal: if flow is otherwise normal on adjacent lanes, this is a true stall, not congestion).

### 7.5 Config schema — camera YAML (full example)

`configs/cameras/junction_cam.yaml`:

```yaml
camera_id: junction_cam
mode: city                      # references configs/modes/city.yaml for default weights/thresholds
source_video: data/processed/scenario_junction_riderdown.mp4
rois:
  road:                          # polygon, pixel coords, clockwise from top-left of frame
    - [120, 200]
    - [1150, 200]
    - [1200, 700]
    - [80, 700]
  exclusion_zones:
    - name: bus_stop
      polygon:
        - [900, 250]
        - [1000, 250]
        - [1000, 340]
        - [900, 340]
count_lines:                     # for the `flow` signal
  - name: north_approach
    p1: [400, 210]
    p2: [700, 210]
  - name: south_approach
    p1: [300, 690]
    p2: [650, 690]
overrides:                        # optional per-camera threshold overrides; omit to use mode defaults
  crowd:
    eps_px: 40
    min_samples: 4
```

`configs/cameras/highway_cam.yaml` follows the same shape but with a `live_lane` polygon instead of `road`, and no `exclusion_zones`/`count_lines` required (flow signal optional in highway mode).

### 7.6 Fusion

`fusion.py` combines the current frame's signal scores into a single incident decision.

```yaml
# configs/modes/city.yaml (excerpt)
fusion:
  weights:
    collision: 0.35
    rider_down: 0.30
    crowd: 0.20
    flow: 0.15
  candidate_threshold: 0.5
  override_rules:                 # any one of these alone is sufficient regardless of weighted sum
    - signal: collision
      min_score: 0.9
    - signal: rider_down
      min_score: 0.85
  cooldown_seconds: 60
  cooldown_grid: [4, 4]           # divide frame into a 4x4 grid; suppress new candidates from the same cell for cooldown_seconds
```

```yaml
# configs/modes/highway.yaml (excerpt)
fusion:
  weights:
    stationary: 0.5
    collision: 0.3
    flow: 0.2
  candidate_threshold: 0.5
  override_rules:
    - signal: collision
      min_score: 0.9
  cooldown_seconds: 60
  cooldown_grid: [4, 4]
```

Weighted sum = `Σ (signal_score × weight)` over currently-active signals for that frame's dominant track cluster. If weighted sum ≥ `candidate_threshold`, OR any override rule is met, produce an `IncidentCandidate`. The cooldown grid prevents the same physical location from re-firing repeatedly while a scene is still resolving.

### 7.7 Severity

`severity.py`, rule table (deterministic, not learned — keeps it explainable for the "why" panel):

| Condition | Severity |
|---|---|
| `rider_down` fired OR a `person` track was one of the colliding tracks (pedestrian hit) | **HIGH** |
| 3+ distinct vehicle tracks involved in the collision cluster | **HIGH** |
| Exactly 2 vehicle tracks collided AND `flow` signal also fired (traffic impact) | **MEDIUM** |
| Everything else that crossed the candidate threshold | **LOW** |

Output includes the specific reasons list from every contributing signal (e.g., `["rider_down: aspect_ratio 1.6 sustained 2.4s", "crowd: cluster +5 in 6s, convergence 0.71", "collision: weak/absent (occluded)"]`) — this reasons list is exactly what the dashboard's WhyPanel renders (§10).

### 7.8 Ring buffer & evidence

`ring_buffer.py` keeps the last 10 s of raw frames in memory (a `collections.deque` sized to `target_fps × 10`). On a fired candidate: write frames from 10 s before the trigger frame through 5 s after (continue buffering 5 more seconds post-trigger before writing) to `data/clips/{incident_id}/evidence.mp4` via OpenCV `VideoWriter`, then re-encode with `ffmpeg` to browser-safe H.264 (`ffmpeg -i raw.mp4 -c:v libx264 -pix_fmt yuv420p -movflags +faststart evidence.mp4`). Also write a single annotated JPEG snapshot (`snapshot.jpg`) at the trigger frame, with bounding boxes and the "why" overlay burned in for a quick-glance thumbnail.

### 7.9 ROI calibration procedure

Because pixel thresholds (`eps_px`, velocity px/frame, ROI polygons) are camera- and resolution-specific, every camera must be calibrated once before use:

1. Run `scripts/annotate_roi.py --video data/processed/<clip>.mp4` — opens the first frame, lets you click points to draw the `road`/`live_lane` polygon, `exclusion_zones`, and `count_lines`; press `s` to save, which writes/updates the corresponding `configs/cameras/*.yaml`.
2. Run the engine against a short clip with `--debug-overlay` (writes an annotated debug video showing every track, signal score, and ROI outline) to sanity-check that thresholds feel right at this camera's actual pixel scale (e.g., is 15 px/frame actually "sudden" at this resolution and camera distance, or does it need adjusting in the mode YAML's per-camera `overrides` block).
3. Adjust `overrides` in the camera YAML, re-run, iterate. Record final values and the reasoning in `PROGRESS.md` next to the relevant task.

### 7.10 Emitter & offline resilience

`emitter.py` POSTs the candidate JSON (see §8.2 for the exact payload) plus evidence file paths to `POST /api/incidents/candidate`. If the API is unreachable (connection refused/timeout), the candidate is appended to a local on-disk queue (`data/queue/pending_incidents.jsonl`) and retried every 5 s; this guarantees no detected incident is silently lost if the API process crashes or is slow to start during rehearsal.

---

## §8. Backend API Design

### 8.1 Endpoints

| Method & Path | Purpose |
|---|---|
| `POST /api/incidents/candidate` | Engine → API. Create incident from a detected candidate. |
| `GET /api/incidents` | List incidents (dashboard load, most-recent-first). |
| `GET /api/incidents/{id}` | Single incident detail (signals, evidence paths, dispatch info if any). |
| `POST /api/incidents/{id}/verify` | Operator confirms or rejects. Body: `{"decision": "confirm" \| "reject"}`. Confirm triggers dispatch. |
| `GET /api/hospitals` | List seeded hospitals. |
| `GET /api/ambulances` | List seeded ambulances + current status/position. |
| `GET /api/metrics/summary` | Eval-derived metrics for the `/metrics` view (reads `eval/` output, see §11). |
| `GET /tiles/{z}/{x}/{y}.png` | Cache-through OSM tile proxy (§4.4). |
| `GET /media/{path}` | Static serving of `data/clips/**` (evidence clips/snapshots). |
| `WS /ws` | Single WebSocket hub; all connected dashboard clients receive all broadcast messages (no per-client filtering needed at this scale). |

### 8.2 WebSocket message envelope

Every message, both directions where applicable, uses:

```json
{ "type": "incident.new", "ts": "2026-07-07T10:15:32.481Z", "payload": { "...": "..." } }
```

**Server → client message types and example payloads:**

`incident.new`
```json
{
  "type": "incident.new",
  "ts": "2026-07-07T10:15:32.481Z",
  "payload": {
    "id": "inc_0001",
    "camera_id": "junction_cam",
    "status": "PENDING_VERIFICATION",
    "severity": "HIGH",
    "scenario_type": "city_riderdown_occluded",
    "location": { "lat": 12.9716, "lon": 77.5946, "label": "MG Road Junction" },
    "reasons": [
      "rider_down: aspect_ratio 1.6 sustained 2.4s",
      "crowd: cluster +5 in 6s, convergence 0.71",
      "collision: weak/absent (occluded)"
    ],
    "signals": { "collision": 0.2, "rider_down": 0.85, "crowd": 0.78, "flow": 0.55 },
    "evidence": {
      "clip_url": "/media/inc_0001/evidence.mp4",
      "snapshot_url": "/media/inc_0001/snapshot.jpg"
    },
    "detected_at": "2026-07-07T10:15:30.100Z"
  }
}
```

`incident.updated`
```json
{
  "type": "incident.updated",
  "ts": "2026-07-07T10:15:41.900Z",
  "payload": { "id": "inc_0001", "status": "DISPATCHED", "dispatch_id": "disp_0001" }
}
```

`ambulance.position`
```json
{
  "type": "ambulance.position",
  "ts": "2026-07-07T10:15:43.000Z",
  "payload": {
    "dispatch_id": "disp_0001",
    "ambulance_id": "amb_03",
    "lat": 12.9702,
    "lon": 77.5931,
    "heading_deg": 47.2,
    "state": "TO_SCENE",
    "eta_seconds": 210
  }
}
```

`corridor.updated`
```json
{
  "type": "corridor.updated",
  "ts": "2026-07-07T10:15:50.000Z",
  "payload": { "dispatch_id": "disp_0001", "junction_id": "jct_014", "signal_state": "GREEN" }
}
```

`hospital.alert`
```json
{
  "type": "hospital.alert",
  "ts": "2026-07-07T10:16:05.000Z",
  "payload": {
    "dispatch_id": "disp_0001",
    "hospital_id": "hosp_02",
    "hospital_name": "St. John's Medical College Hospital",
    "severity": "HIGH",
    "incident_type": "rider_down",
    "eta_seconds": 480
  }
}
```

### 8.3 SQLite schema (SQLAlchemy models, `services/api/models.py`)

| Table | Key columns |
|---|---|
| `incidents` | `id` (PK, e.g. `inc_0001`), `camera_id`, `status`, `severity`, `scenario_type`, `lat`, `lon`, `location_label`, `evidence_clip_path`, `evidence_snapshot_path`, `detected_at`, `verified_at`, `verify_decision` |
| `incident_signals` | `id` (PK), `incident_id` (FK), `signal_name`, `score`, `reasons` (JSON text) |
| `dispatches` | `id` (PK, e.g. `disp_0001`), `incident_id` (FK), `ambulance_id` (FK), `hospital_id` (FK), `route_geojson` (text), `state`, `created_at`, `arrived_scene_at`, `departed_scene_at`, `arrived_hospital_at` |
| `ambulances` | `id` (PK), `name`, `home_lat`, `home_lon`, `status` (`IDLE`/`BUSY`), `current_lat`, `current_lon` |
| `hospitals` | `id` (PK), `name`, `lat`, `lon`, `trauma_level` (`1`/`2`/`general`) |
| `corridor_junctions` | `id` (PK), `lat`, `lon`, `name` |
| `eval_runs` | `id` (PK), `run_at`, `manifest_path`, `results_json` (text) — written by `eval/run_eval.py`, read by `GET /api/metrics/summary` |

### 8.4 Verify endpoint behavior (state machine trigger)

`POST /api/incidents/{id}/verify` with `{"decision": "reject"}` → status `REJECTED`, no further action, broadcast `incident.updated`.

`{"decision": "confirm"}` →
1. status → `CONFIRMED`, broadcast `incident.updated`.
2. Call `sim/ambulance.py::dispatch(incident)` synchronously to pick ambulance + hospital + route (fast, no need to be async — routing call has its own short timeout/fallback per §9.1) and create the `dispatches` row; status → `DISPATCHED`, broadcast `incident.updated` with `dispatch_id`.
3. Start an asyncio background task running the ambulance mover loop for this dispatch (§9.1); it in turn triggers the corridor sequencer (§9.2) and hospital pre-alert (§9.3) at the appropriate state transitions.

### 8.5 Shared type contract

`services/api/schemas.py` (Pydantic) is the canonical definition of every payload shown in §8.2. `apps/dashboard/src/types/events.ts` mirrors it by hand (no codegen needed at this scale — the shapes above are the contract both sides implement). Any change to a payload shape must be made in both places in the same task.

---

## §9. Simulation Design

### 9.1 Ambulance mover (`services/api/sim/ambulance.py`)

- **Seed data** `data/seed/ambulances.json`: 5 mock units at real Bengaluru hospital/staging coordinates, e.g.:
```json
[
  { "id": "amb_01", "name": "Ambulance 1", "home_lat": 12.9634, "home_lon": 77.5855 },
  { "id": "amb_02", "name": "Ambulance 2", "home_lat": 12.9757, "home_lon": 77.6011 },
  { "id": "amb_03", "name": "Ambulance 3", "home_lat": 12.9279, "home_lon": 77.6271 },
  { "id": "amb_04", "name": "Ambulance 4", "home_lat": 13.0067, "home_lon": 77.5709 },
  { "id": "amb_05", "name": "Ambulance 5", "home_lat": 12.9147, "home_lon": 77.6497 }
]
```
- **Selection:** on confirm, compute haversine distance from the incident location to every `IDLE` ambulance's `current_lat/lon` (initially = `home_lat/lon`); pick nearest.
- **Routing:** `sim/routing.py::get_route(origin, dest)` tries live OSRM (`GET /route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson`, 2 s timeout); on any exception/timeout, loads the matching pre-cached GeoJSON from `data/routes/` (matched by rounding origin/dest to the nearest seeded ambulance/incident-location pair — since the demo only ever uses a small fixed set of scenario locations, exact-match caching is sufficient; no need for general route-cache indexing).
- **Movement:** interpolate along the route polyline at 35 km/h base speed; multiply by 1.4× on any segment currently flagged `GREEN` by the corridor sequencer (simulates the real benefit of a green corridor). Tick once per second (asyncio `sleep(1)`), computing new position by walking cumulative polyline distance, and broadcast `ambulance.position`.
- **States:** `TO_SCENE` → (on reaching the incident's lat/lon within ~15 m) `AT_SCENE` for a fixed 45 s dwell (this is when `hospital.alert` fires, per §3.2 step 7) → `TO_HOSPITAL` (new route computed from scene to the pre-selected hospital) → `ARRIVED` (incident status → `RESOLVED`, broadcast `incident.updated`).

### 9.2 Green corridor sequencer (`services/api/sim/corridor.py`)

- **Junction set:** `data/seed/junctions.json`, populated once by `scripts/seed_junctions.py` (Overpass query for `highway=traffic_signals` nodes within a bounding box covering the demo's actual route corridors — this is a one-time build-time data pull, never called live during the demo). Fallback: if Overpass is unreachable at build time, hand-curate ~20 real major Bengaluru junctions (e.g., Trinity Circle, Domlur, Old Airport Road junctions, Silk Board approach junctions) with coordinates from any map, and commit that as `data/seed/junctions.json` directly — either path produces the same file shape:
```json
[
  { "id": "jct_014", "name": "Trinity Circle", "lat": 12.9721, "lon": 77.6190 }
]
```
- **Logic:** every ambulance-position tick, for each junction within 30 m of the route polyline, compute route-distance from the ambulance's current polyline position to that junction. If ≤ 500 m and not already `GREEN`, set `GREEN` and broadcast `corridor.updated`. 10 s after the ambulance's position passes a junction (route-distance goes negative / behind), revert it to default and broadcast again.

### 9.3 Hospital pre-alert (`services/api/sim/hospital.py`)

- **Seed data** `data/seed/hospitals.json`: ~8 real Bengaluru trauma-capable hospitals, e.g. NIMHANS, St. John's Medical College Hospital, Victoria Hospital, Manipal Hospital Old Airport Road, with `trauma_level`.
- **Selection (at dispatch time, step 2 of §8.4):** nearest hospital to the incident location whose `trauma_level` matches severity (HIGH → trauma_level 1 preferred, falls back to nearest regardless if none within a reasonable radius — keep the matching rule simple: sort by distance, prefer trauma_level 1 for HIGH severity, otherwise just nearest).
- **Firing:** triggered by the ambulance reaching `AT_SCENE` (§9.1) — pre-alert is meant to arrive well before the ambulance does, giving the hospital advance warning during transport, so it fires at scene-arrival, not at dispatch. Payload carries live `eta_seconds` computed from remaining route distance at base speed (updates are not pushed again after firing in the MVP — the dashboard's own countdown timer, driven off the initial `eta_seconds` and clock, is sufficient; this keeps the simulator simple).

---

## §10. Frontend Design

### 10.1 App shell

`apps/dashboard/src/main.tsx` sets up `react-router-dom` with 4 routes. A single `useWebSocket` hook (`src/lib/ws.ts`) opens `ws://localhost:8000/ws` once, auto-reconnects with backoff on close, and dispatches every incoming message into the Zustand store (`src/store/index.ts`). All 4 routes read from the same store — the demo runs all 3 non-metrics routes in separate browser windows, all sharing the same live WebSocket-driven state independently (each window opens its own WS connection; the store lives per-tab, which is fine since state is derived entirely from server broadcasts).

**Zustand store shape** (`src/store/index.ts`):
```ts
interface Store {
  incidents: Record<string, Incident>;
  ambulances: Record<string, AmbulanceState>;
  corridorJunctions: Record<string, 'GREEN' | 'DEFAULT'>;
  hospitalAlerts: HospitalAlert[];
  wsStatus: 'connecting' | 'open' | 'closed';
}
```

### 10.2 `/control` — Control Room

- **FeedGrid**: HTML5 `<video>` tiles autoplaying the two scenario source files (`data/processed/scenario_*.mp4`, served via `/media` or a Vite public copy) side by side, labeled by camera_id — this is the "live camera feed" illusion.
- **IncidentFeed**: a list of incident cards (most recent first), each showing severity color, camera, timestamp, one-line reason summary.
- **IncidentDetail**: clicking a card opens a detail pane with the **WhyPanel** — one horizontal bar per signal (`collision`, `rider_down`, `crowd`, `flow`/`stationary`) showing its score 0–1, plus the reasons list as bullet text underneath. This is the single most important UI element for explaining the crowd-as-signal novelty live.
- **VerifyModal**: shows the evidence clip (`<video controls autoplay>` pointed at `evidence.clip_url`) and two large buttons, Confirm / Reject, calling `POST /api/incidents/{id}/verify`.

### 10.3 `/dispatch` — Map

- MapLibre GL map, tile source pointed at `/tiles/{z}/{x}/{y}.png` (never the public OSM host).
- Ambulance marker: position updated on every `ambulance.position` message; interpolate visually between the last two known points over the 1 s tick interval (a simple `requestAnimationFrame` tween) so movement looks smooth rather than jumping once per second.
- Route polyline drawn from the dispatch's `route_geojson`.
- Corridor junction dots: colored from the store's `corridorJunctions` map, red (default) → green.
- Incident marker (severity-colored pin) and hospital marker.
- **ETA banner** and a **crash-to-dispatch stopwatch**: starts counting at `incident.new`, stops at the `incident.updated` message carrying status `DISPATCHED` — this stopwatch reading is the headline number of the whole demo and must be visibly large on screen.

### 10.4 `/hospital` — Hospital Console

- Dark console theme. Pre-alert cards appear on `hospital.alert`, color-coded by severity, showing hospital name, incident type, severity, and a live ETA countdown (client-side timer seeded from the message's `eta_seconds`). A static mock "prep checklist" (trauma bay ready, blood bank notified, etc.) appears under HIGH severity cards for visual richness — purely cosmetic, no backend logic needed.

### 10.5 `/metrics`

- Plain tables rendered from `GET /api/metrics/summary`: detection latency per scenario type, TPR/FAR on the held-out set, the direct-vs-crowd-signal comparison table, occlusion-robustness count, simulated crash-to-dispatch time vs. the 8–15 minute baseline. This is the "closing slide" data, live-queryable rather than a static image.

### 10.6 Visual style guide

- Dark background (`bg-slate-900`/`bg-black` family) across all three operational views — reads as "control room," not "consumer app."
- Severity color tokens used consistently everywhere: HIGH = red (`#ef4444`), MEDIUM = amber (`#f59e0b`), LOW = slate/gray (`#94a3b8`).
- Incident cards use large type (panel will be reading this from a distance across a room) — minimum 16px body text, 24px+ for severity labels and the stopwatch.

---

## §11. Evaluation Harness

`eval/run_eval.py`:
1. Reads `data/manifests/eval_manifest.csv`.
2. For each row, runs the detection engine **headless** (no API POST, no display window — a `--headless` engine mode that just logs candidate events with timestamps to a local results structure instead of emitting over HTTP) against `clip_path` using the specified `camera_config`.
3. Records: whether any candidate fired (predicted label), the first-fire timestamp relative to clip start, and which signals contributed.
4. Compares to `gt_label`/`gt_event_time_s` to compute, written to `eval/results/{run_id}.json` and echoed as markdown tables:
   - **Detection latency** = first-fire timestamp − `gt_event_time_s`, averaged per `scenario_type`.
   - **TPR / FAR**: TPR = fired-positives / total-positives; FAR = fired-on-negatives / total-negatives — computed once overall, and again **split into "direct-only" (collision/rider_down/stationary/flow without crowd) vs. "crowd-assisted" (crowd contributed to the firing decision)** — this split is itself a reported finding per the project brief.
   - **Occlusion robustness**: count of clips tagged `*_occluded` in `scenario_type` where `crowd` fired but `collision` stayed below its individual threshold — the core novelty claim, quantified directly.
   - **Simulated crash-to-dispatch time**: read from the stopwatch value logged by a full live-loop run (engine → API → verify → dispatch), reported honestly as "simulated, human-verification-included" against the commonly cited 8–15 minute call-based reporting baseline (cited in the report from road-safety literature, not measured by this project).
5. Writes a summary row into the `eval_runs` SQLite table so `GET /api/metrics/summary` can serve the latest run to `/metrics` without re-running eval live.

`eval/metrics.py` holds the pure calculation functions (kept separate from the CLI/reporting glue in `run_eval.py` so they're unit-testable).

---

## §12. Near-Miss Mini-Study

`eval/near_miss/conflicts.py`, run against self-recorded junction footage (§6.4):

- **Conflict definition (Post-Encroachment-Time proxy):** two tracks whose paths cross the same spatial grid cell (reuse the fusion cooldown grid concept, e.g. a finer 20×20 grid over the ROI) within **< 1.5 s** of each other, where at least one of the two tracks has speed above a small "actually moving" threshold (rules out two stationary/queued tracks technically sharing a cell).
- Run over N hours of collected footage (target: at least 4–6 hours across at least 2 times of day per the data-collection protocol).
- **Outputs**, written to `eval/near_miss/study.md`:
  - Conflicts-per-hour table, broken down by time-of-day bucket (morning/midday/evening) and by movement-type pairing (pedestrian–vehicle, vehicle–vehicle, two-wheeler–vehicle).
  - A conflict-point heatmap: overlay conflict locations as a density plot on a representative junction frame (matplotlib scatter/hexbin over the still image, saved as a PNG).
- This feeds one standalone report chapter ("near-miss analytics") separate from the incident-detection evaluation chapter.

---

## §13. Build Order — Epics & Tasks

Work through these in order. Each task: **Goal**, **Files**, **Steps**, **Acceptance check**. Section references point back to the detailed spec above — read the referenced section before starting the task if anything is unclear.

### E0 — Scaffold

**E0-T1. Repo init & gitignore**
- Files: `.gitignore`, `README.md`.
- Steps: `git init` in the project root; write `.gitignore` covering `venv/`, `node_modules/`, `models/`, `data/raw/`, `data/tile_cache/`, `data/clips/`, `*.pyc`, `__pycache__/`, `.env`; write a short `README.md` (project name, one-paragraph description, how to run — filled in properly at E10).
- Acceptance: `git status` shows a clean initial commit; `.gitignore` present.

**E0-T2. Directory scaffold**
- Files: every folder in §5, with `.gitkeep` in empty ones.
- Steps: create the full tree from §5 exactly.
- Acceptance: `tree /F` (or equivalent) matches §5.

**E0-T3. Python environment + CUDA verification**
- Files: `requirements.txt` (see Appendix C for the full pinned list).
- Steps: `python -m venv venv`; `venv\Scripts\Activate.ps1`; install PyTorch from the CUDA-specific index URL matching the local driver (check with `nvidia-smi` first for the CUDA version, then use the matching `--index-url https://download.pytorch.org/whl/cuXXX`); then `pip install -r requirements.txt` for the rest.
- Acceptance: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"` prints `True` and a real GPU name.

**E0-T4. Vite dashboard scaffold**
- Files: `apps/dashboard/` (Vite-generated) + Tailwind config.
- Steps: `npm create vite@latest apps/dashboard -- --template react-ts`; `npm install`; add Tailwind (`npm install -D tailwindcss postcss autoprefixer`, `npx tailwindcss init -p`, wire `tailwind.config.js` content globs to `src/**/*.{ts,tsx}`); install `react-router-dom maplibre-gl zustand`.
- Acceptance: `npm run dev` serves the default Vite page at `http://localhost:5173` with Tailwind base styles applying (test with one utility class on the default page).

**E0-T5. Model download script**
- Files: `scripts/download_models.py`.
- Steps: script that downloads `yolo11s.pt` and `yolo11s-pose.pt` via `ultralytics` (they auto-download on first `YOLO("yolo11s.pt")` call, so this script can simply instantiate both once to trigger caching into `models/` — set `ultralytics` config to use `models/` as the weights dir, or just move the auto-downloaded files there after).
- Acceptance: `models/yolo11s.pt` and `models/yolo11s-pose.pt` exist on disk after running the script.

### E1 — Video + Detection Core

**E1-T1. Video source with real-time pacing**
- Files: `services/detection/video_source.py`.
- Steps: implement per §7.2 — reads a video file with OpenCV, yields frames paced to the source FPS × `speed_factor`, exposes `target_fps`-based frame skipping.
- Acceptance: running it standalone against any test video prints frame timestamps advancing at approximately real-time (±10%) for `speed_factor=1.0`.

**E1-T2. Detector + tracker wrapper**
- Files: `services/detection/detector.py`.
- Steps: implement per §7.3 — wraps `YOLO(weights).track(...)`, returns per-frame track list (id, cls, bbox, conf).
- Acceptance: run against any short traffic clip; printed output shows stable track IDs persisting across frames for the same vehicle/person.

**E1-T3. FrameContext / track-history builder**
- Files: `services/detection/tracker_ctx.py`.
- Steps: implement per §7.4 intro — maintains rolling history per track_id (position, bbox, velocity smoothed over last 5 frames, aspect ratio), exposes `FrameContext` for the current frame.
- Acceptance: unit test with a synthetic sequence of bboxes moving at a known pixel/frame rate asserts computed velocity matches within tolerance.

**E1-T4. Debug overlay / annotated output**
- Files: add `--debug-overlay` flag wiring in `services/detection/engine.py` (skeleton engine loop calling T1–T3 only at this point) using `supervision`'s annotators (or manual OpenCV drawing) to draw boxes + track IDs + velocity vectors, writing an output video.
- Acceptance: running the engine with `--debug-overlay` on a test clip produces a playable annotated MP4 showing correct boxes/IDs.

### E2 — Signals (Direct)

**E2-T1. Signal base interface + synthetic test fixtures**
- Files: `services/detection/signals/base.py`, `tests/conftest.py` (or a shared fixtures module) with a helper to build synthetic `FrameContext` sequences (e.g., two tracks converging then one stopping) without needing any video.
- Steps: implement the `Signal`/`SignalResult` interface from §7.4.
- Acceptance: a trivial no-op signal subclass can be constructed and called against a synthetic fixture in a pytest test.

**E2-T2. Collision signal**
- Files: `services/detection/signals/collision.py`, `tests/test_signals_collision.py`.
- Steps: implement per §7.4 collision spec.
- Acceptance: pytest with a synthetic two-vehicle-converge-then-stop fixture yields a score ≥ 0.9; a synthetic normal-passing-traffic fixture yields a score below `candidate_threshold`.

**E2-T3. Stationary signal**
- Files: `services/detection/signals/stationary.py`, `tests/test_signals_stationary.py`.
- Steps: implement per §7.4 stationary spec.
- Acceptance: pytest fixture with a track motionless for 20 s inside a `live_lane` polygon yields score ≥ 0.9; a fixture with normal stop-and-go (moves again after 4 s) yields no fire.

**E2-T4. Flow signal**
- Files: `services/detection/signals/flow.py`, `tests/test_signals_flow.py`.
- Steps: implement per §7.4 flow spec (count-line crossing + rolling median).
- Acceptance: pytest fixture with a sudden drop to near-zero crossings after an established baseline rate fires; steady-state traffic does not.

### E3 — Signals (Novel) — **Gate epic**

**E3-T1. Crowd-as-signal**
- Files: `services/detection/signals/crowd.py`, `tests/test_signals_crowd.py`.
- Steps: implement per §7.4 crowd spec (DBSCAN clustering + formation-rate + convergence check).
- Acceptance: pytest fixture simulating 5 pedestrian tracks converging on a point within 6 s fires with score ≥ 0.7; a fixture with 10 pedestrians walking in parallel (no convergence) does not fire.

**E3-T2. Rider-down heuristic**
- Files: `services/detection/signals/rider_down.py`, `tests/test_signals_rider_down.py`.
- Steps: implement per §7.4 rider_down spec (aspect-ratio flip + proximity + immobility), excluding pose confirmation for this task.
- Acceptance: pytest fixture with a person track's aspect ratio flipping to 1.6 and staying near a decelerating motorcycle track fires ≥ 0.85; a fixture of a person merely crouching briefly (aspect flip lasting < 1 s) does not fire.

**E3-T3. Pose confirmation + real-clip gate**
- Files: extend `services/detection/signals/rider_down.py` with the pose-model check per §7.4; wire the debug-overlay engine to run all signals now.
- Steps: add the `yolo11s-pose` crop-and-check every 3rd frame while the primary heuristic is active, per §7.4.
- Acceptance (**epic gate — do not proceed to E4 until this passes**): run the full engine (all signals wired, debug overlay on) against the occluded rider-down clip named in the manifest (`scenario_junction_riderdown.mp4` / the staged occluded clip) and confirm: `crowd` signal score crosses its threshold, `collision` signal stays below its individual override threshold (impact was occluded), and the combined weighted-fusion-equivalent (compute by hand from logged scores, fusion module itself lands in E4) would cross `candidate_threshold`. Log this confirmation in `PROGRESS.md`.

### E4 — Fusion + Evidence

**E4-T1. Fusion module**
- Files: `services/detection/fusion.py`, `tests/test_fusion.py`.
- Steps: implement per §7.6 — weighted sum, override rules, cooldown grid, reading weights from the active mode YAML.
- Acceptance: pytest asserts (a) a case below all individual overrides but with combined weighted sum ≥ 0.5 produces a candidate, (b) a second candidate from the same grid cell within `cooldown_seconds` is suppressed, (c) after cooldown expires a new candidate from that cell is allowed.

**E4-T2. Severity module**
- Files: `services/detection/severity.py`.
- Steps: implement the rule table from §7.7, producing severity + reasons list.
- Acceptance: unit test for each row of the severity table (rider-down → HIGH, 3+ vehicles → HIGH, 2-vehicle+flow → MEDIUM, else → LOW).

**E4-T3. Ring buffer + evidence writer**
- Files: `services/detection/ring_buffer.py`.
- Steps: implement per §7.8 — in-memory deque, write pre/post-trigger MP4, ffmpeg re-encode, annotated snapshot JPEG.
- Acceptance: triggering a synthetic candidate mid-stream against a test video produces a playable `evidence.mp4` (verify with `ffprobe` or by opening it) spanning roughly 15 s, and a valid `snapshot.jpg`.

**E4-T4. Emitter with offline queue**
- Files: `services/detection/emitter.py`.
- Steps: implement per §7.10 — POST to API, on-disk retry queue if unreachable.
- Acceptance: with no API running, trigger a candidate — confirm it lands in `data/queue/pending_incidents.jsonl`; start a stub HTTP server, confirm the queued item is delivered within one retry interval.

### E5 — API Core

**E5-T1. FastAPI app + SQLAlchemy models**
- Files: `services/api/main.py`, `services/api/db.py`, `services/api/models.py`.
- Steps: set up FastAPI app, SQLite engine/session, all tables from §8.3.
- Acceptance: `uvicorn services.api.main:app --reload` starts cleanly; SQLite file created with all tables present (verify via `sqlite3` `.tables`).

**E5-T2. Candidate endpoint + persistence**
- Files: `services/api/schemas.py`, `services/api/routers/incidents.py`.
- Steps: implement `POST /api/incidents/candidate` per §8.1/§8.2, persisting to `incidents` + `incident_signals`.
- Acceptance: POST the example JSON from §8.2's `incident.new` payload shape (as the candidate submission format) via `curl`/Postman; confirm a row appears in `incidents` and matching rows in `incident_signals`.

**E5-T3. WebSocket hub**
- Files: `services/api/ws.py`.
- Steps: connection manager (accept, track connected clients, broadcast helper); wire the candidate endpoint to broadcast `incident.new` on creation.
- Acceptance: connect with a WS test client (or browser devtools) to `/ws`, POST a candidate, confirm the `incident.new` message arrives with the exact shape from §8.2.

**E5-T4. Verify endpoint + state machine skeleton**
- Files: `services/api/routers/incidents.py` (extend).
- Steps: implement `POST /api/incidents/{id}/verify` per §8.4 — for now (before E6 exists) just implement the `reject` path fully and the `confirm` path up through status → `CONFIRMED` with a broadcast (dispatch creation deferred to E6-T2, hook the call in but it can no-op/stub until E6 lands — note as such in PROGRESS.md, then close the loop in E6).
- Acceptance: reject flips status to `REJECTED` and broadcasts `incident.updated`; confirm flips to `CONFIRMED` and broadcasts.

**E5-T5. Static media + tile proxy**
- Files: `services/api/routers/tiles.py`, static mount in `main.py`.
- Steps: mount `data/clips/` at `/media`; implement `GET /tiles/{z}/{x}/{y}.png` per §4.4 (fetch-through cache to `data/tile_cache/`).
- Acceptance: after one request for a given `{z}/{x}/{y}`, confirm the PNG is cached on disk and a second request (with network disabled, e.g. via a firewall rule or by pointing the upstream URL at an invalid host temporarily) still succeeds from cache.

### E6 — Simulators

**E6-T1. Seed data files**
- Files: `data/seed/hospitals.json`, `data/seed/ambulances.json`, `scripts/seed_junctions.py`, `data/seed/junctions.json`.
- Steps: write the hospital/ambulance seed files per §9.1/§9.3 with real Bengaluru coordinates; implement and run `seed_junctions.py` (Overpass query, with the hand-curated fallback per §9.2 if Overpass access fails) to produce `junctions.json`.
- Acceptance: all three JSON files exist, parse, and contain the counts specified in §9 (5 ambulances, ~8 hospitals, ~20 junctions); load a startup script that inserts them into the `ambulances`/`hospitals`/`corridor_junctions` tables and confirm row counts match.

**E6-T2. Routing client + route prefetch**
- Files: `services/api/sim/routing.py`, `scripts/prefetch_routes.py`, `data/routes/*.geojson`.
- Steps: implement `get_route()` per §9.1 (live OSRM with 2 s timeout, GeoJSON fallback); implement and run the prefetch script for every ambulance-home ↔ demo-incident-location and incident-location ↔ hospital pair actually used by the two demo scenarios.
- Acceptance: with network available, `get_route()` returns a valid polyline for a demo pair; with the OSRM host made unreachable (e.g. temporarily point at a bad URL in a test), it falls back to the cached GeoJSON and still returns a valid polyline.

**E6-T3. Ambulance mover**
- Files: `services/api/sim/ambulance.py`.
- Steps: implement per §9.1 — selection, dispatch creation, asyncio 1 Hz movement loop, state transitions, broadcasting `ambulance.position`. Wire into E5-T4's confirm path (replacing the stub).
- Acceptance: confirm an incident end-to-end via the API; observe `ambulance.position` messages arriving once per second over `/ws` with monotonically progressing coordinates toward the incident location, then toward the hospital after the 45 s scene dwell.

**E6-T4. Corridor sequencer**
- Files: `services/api/sim/corridor.py`.
- Steps: implement per §9.2, hooked into the ambulance mover's tick loop.
- Acceptance: during a confirmed-dispatch run, observe at least one `corridor.updated` message with `GREEN` as the ambulance approaches a seeded junction within 500 m of the route, and a reversion message after it passes.

**E6-T5. Hospital pre-alert**
- Files: `services/api/sim/hospital.py`.
- Steps: implement per §9.3, hooked to the `AT_SCENE` transition.
- Acceptance: during a confirmed-dispatch run, observe exactly one `hospital.alert` message firing at the moment the ambulance reaches `AT_SCENE` state, with a plausible `eta_seconds`.

### E7 — Dashboard

**E7-T1. App shell, router, WS store**
- Files: `apps/dashboard/src/main.tsx`, `src/store/index.ts`, `src/lib/ws.ts`, `src/types/events.ts`.
- Steps: implement per §10.1 — routes, Zustand store shape, WS hook with reconnect, TS types mirroring §8.2/§8.3.
- Acceptance: navigating to `/control`, `/dispatch`, `/hospital`, `/metrics` renders (even if empty) without console errors; opening devtools shows a successful WS connection to `/ws`.

**E7-T2. Control room — feed grid + incident cards**
- Files: `apps/dashboard/src/views/Control.tsx`, `src/components/FeedGrid.tsx`, `src/components/IncidentFeed.tsx`.
- Steps: implement per §10.2 (FeedGrid + IncidentFeed only this task).
- Acceptance: with the API running and a manually-POSTed candidate, the new incident appears in the IncidentFeed list within one WS round-trip, correctly color-coded by severity.

**E7-T3. WhyPanel + VerifyModal**
- Files: `src/components/WhyPanel.tsx`, `src/components/VerifyModal.tsx`.
- Steps: implement per §10.2.
- Acceptance: clicking an incident card opens the WhyPanel with correct per-signal bars matching the POSTed scores; clicking Confirm in VerifyModal successfully calls the verify endpoint and the card's status updates live.

**E7-T4. Dispatch map + ambulance animation**
- Files: `apps/dashboard/src/views/Dispatch.tsx`, `src/components/MapView.tsx`.
- Steps: implement per §10.3 — MapLibre setup pointed at `/tiles`, ambulance marker with tween animation, route polyline.
- Acceptance: after confirming an incident, watch the ambulance marker move smoothly along the drawn route on the map in real time.

**E7-T5. Corridor + hospital markers + ETA/stopwatch**
- Files: extend `src/components/MapView.tsx`; `src/components/EtaBanner.tsx`, `src/components/Stopwatch.tsx`.
- Steps: implement per §10.3 remainder.
- Acceptance: junction dots flip color live during a dispatch run; the crash-to-dispatch stopwatch starts on `incident.new` and freezes at the correct elapsed time on the `DISPATCHED` update.

**E7-T6. Hospital console**
- Files: `apps/dashboard/src/views/Hospital.tsx`, `src/components/PreAlertCard.tsx`.
- Steps: implement per §10.4.
- Acceptance: the pre-alert card appears at the correct moment (scene arrival) with a live-counting-down ETA.

**E7-T7. Metrics view**
- Files: `apps/dashboard/src/views/Metrics.tsx`.
- Steps: implement per §10.5, fetching `GET /api/metrics/summary`.
- Acceptance: with at least one eval run recorded (dummy data acceptable at this point, real data after E9), the tables render correctly.

### E8 — Scenario Content — **Gate epic**

**E8-T1. Dataset acquisition**
- Steps: download/organize CADP (and as many secondary datasets as time allows) into `data/raw/`; run `scripts/make_clips.py` to normalize a working subset into `data/processed/`; populate `data/manifests/eval_manifest.csv` per §6.2.
- Acceptance: `data/manifests/eval_manifest.csv` has at least 15–20 rows spanning both positive and negative examples across `city_collision`, `city_riderdown_occluded`, `highway_stationary`, and negative scenario types.

**E8-T2. Camera ROI configs for the two demo cameras**
- Steps: run `scripts/annotate_roi.py` (E1's calibration tool, built alongside detection but exercised properly here once real demo clips exist) against the chosen junction and highway demo clips; iterate per the §7.9 calibration procedure.
- Acceptance: `configs/cameras/junction_cam.yaml` and `configs/cameras/highway_cam.yaml` are fully populated (ROIs, count-lines, overrides) and the debug-overlay engine run against each shows sensible track/ROI alignment.

**E8-T3. Scenario 1 — junction rider-down, occluded (end-to-end)**
- Steps: pick or stage the final occluded rider-down clip; run the full engine → API → dashboard chain live; tune fusion/severity thresholds if needed (update YAML per §7.9, never hardcode).
- Acceptance: the full 5-beat sequence from §1.5 (steps 1–5) runs live end-to-end without manual intervention beyond the operator's one Confirm tap.

**E8-T4. Scenario 2 — highway stationary vehicle (end-to-end) — epic gate**
- Steps: same as T3 for the highway clip and `highway.yaml` mode.
- Acceptance (**epic gate**): both demo scenarios run end-to-end back-to-back without manual intervention (beyond switching which video plays and the operator's Confirm tap), matching all 7 beats of §1.5. Log confirmation in `PROGRESS.md`.

### E9 — Evaluation

**E9-T1. Eval runner**
- Files: `eval/run_eval.py`, `eval/metrics.py`, headless engine mode.
- Steps: implement per §11.
- Acceptance: `python eval/run_eval.py --manifest data/manifests/eval_manifest.csv` completes and writes `eval/results/{run_id}.json`.

**E9-T2. Metrics report + API wiring**
- Files: extend `eval/run_eval.py` to also write an `eval_runs` row; `services/api/routers/metrics.py`.
- Steps: implement `GET /api/metrics/summary` reading the latest `eval_runs` row.
- Acceptance: `/metrics` in the dashboard shows real numbers (latency, TPR/FAR, direct-vs-crowd split, occlusion-robustness count) from an actual eval run, not dummy data.

**E9-T3. Near-miss study**
- Files: `eval/near_miss/conflicts.py`, `eval/near_miss/study.md`.
- Steps: implement per §12; run against collected junction footage; write up findings.
- Acceptance: `study.md` contains the conflicts-per-hour table and the heatmap image, generated from real self-recorded footage (minimum 4 hours per §12).

### E10 — Polish + Demo Insurance

**E10-T1. Demo runbook script**
- Files: `scripts/run_demo.ps1`.
- Steps: one script that activates the venv, starts the API (`uvicorn`), starts the dashboard dev server, and opens the three browser routes in separate windows — per the exact sequence in §14.
- Acceptance: running the script from a clean shell brings up a fully working demo environment with zero manual steps beyond pressing Confirm during the run.

**E10-T2. Rehearsal checklist + backup video**
- Files: `docs/demo_script.md` (finalize), a recorded backup video (store path noted in `docs/demo_script.md`, file itself outside git if large).
- Steps: rehearse the full demo at least 5–10 times per the brief's phase-gate guidance; on a clean, flawless run, screen-record the entire sequence as the insurance video.
- Acceptance: a backup video file exists, plays back correctly, and shows the full 7-beat sequence without errors.

**E10-T3. Report skeleton fill-in**
- Files: `docs/report_skeleton.md`, `docs/literature_notes.md`, `docs/dataset_notes.md`, `docs/future_work.md`.
- Steps: fill in the report skeleton using real numbers from E9, the architecture from this plan, and the vision/future-work content from the original brief's §10 (describe-bucket items only).
- Acceptance: report skeleton has no remaining `TODO` placeholders in its metrics/results sections.

**E10-T4 (stretch, optional). IDD fine-tuning**
- Steps: only attempt if all prior epic gates passed with time remaining. Register for IDD access, fine-tune YOLO11 on India-specific classes (auto-rickshaw, animal), swap into `configs/modes/*.yaml` as an alternate weights file, re-run E9 eval to compare against the base COCO-class model.
- Acceptance: a documented before/after comparison in `docs/report_skeleton.md`'s stretch-goals section. Skippable entirely without affecting any other epic.

---

## §14. Demo Runbook

**Pre-flight checks (run before every rehearsal and before the real demo):**
1. `nvidia-smi` shows the GPU idle and available.
2. Ports 8000 (API) and 5173 (dashboard dev server) are free.
3. Tile cache is warm: pan/zoom the `/dispatch` map once over the full demo route area beforehand so `data/tile_cache/` has every tile needed.
4. `data/routes/*.geojson` exist for every demo pair (confirms the offline routing fallback is ready even if OSRM's public server is slow/down on demo day).
5. Evidence clip storage (`data/clips/`) is writable and has free disk space.

**Window layout:** 3 browser windows arranged so the panel can see all three at once (or projected in sequence) — `/control` (primary, where the operator sits), `/dispatch` (map, the visual centerpiece), `/hospital` (console).

**Sequence:** follow the 7 beats in §1.5 exactly; the only manual actions are (a) starting scenario 1's video playback, (b) tapping Confirm in the VerifyModal, (c) switching to scenario 2's video, (d) tapping Confirm again, (e) advancing to the closing `/metrics` slide.

**Failure playbook:**
- API process dies mid-demo → restart with `scripts/run_demo.ps1`'s API command alone; the dashboard's WS auto-reconnects; in-progress dispatch state is lost but a fresh Confirm on a new candidate works immediately.
- Routing/tiles network hiccup → invisible to the audience; both are cache-backed per §4.4/§9.1, no action needed.
- Total environment failure → cut to the backup insurance video from E10-T2; narrate over it exactly as the live demo would have gone.

---

## §15. Testing Strategy, Risk Register, Appendices

### 15.1 Testing strategy

- **Signal unit tests** (`tests/test_signals_*.py`): synthetic `FrameContext` sequences, no video needed — fast, deterministic, run on every change to a signal module.
- **Fusion/severity unit tests**: synthetic signal-score inputs, verifying the fusion math and cooldown/override logic directly.
- **API tests** (`tests/test_api_incidents.py`): `httpx`-based tests against the FastAPI app (using FastAPI's `TestClient`) covering the candidate → persist → broadcast and verify → state-transition flows.
- **One end-to-end smoke script**: starts engine (headless, one clip) + API together, confirms an incident row is created and reaches `CONFIRMED` via a scripted verify call — run this after any change touching the engine↔API contract.

### 15.2 Risk register (mapped to this architecture's mitigations)

| Risk (from the brief) | Mitigation in this plan |
|---|---|
| Scope creep | Build/Simulate/Describe buckets (§1.4) enforced per-task; new ideas → `docs/future_work.md` only. |
| False alarms undermining the demo | Human verification step (§8.4) is load-bearing by design; thresholds tuned against the held-out manifest (§11) before demo content is finalized (E8 before E9, but E9's metrics feed back into any final threshold tuning noted in PROGRESS.md). |
| Data scarcity for rare real events | Three parallel dataset tracks (§6.1) plus staged/clearly-labeled clips; crowd/flow indirect signals work on ordinary footage too, reducing dependence on rare real-crash footage. |
| Live-demo fragility | Tile cache + route cache (§4.4/§9.1/§9.2) remove network dependency; recorded backup video (E10-T2); demo machine frozen after final rehearsal. |
| Losing momentum on a flexible timeline | Epic gates in §13 (E3, E8) are hard go/no-go checkpoints mirroring the brief's phase gates; `PROGRESS.md` is the running status artifact to share with a supervisor. |

### 15.3 Appendix A — full WebSocket/REST JSON examples

See §8.2 for `incident.new`, `incident.updated`, `ambulance.position`, `corridor.updated`, `hospital.alert` — these five are exhaustive; no other server→client message types exist in the MVP. Client→server traffic is REST only (no client-originated WS messages needed).

### 15.4 Appendix B — full example configs

See §7.5 for the complete `junction_cam.yaml` example and §7.6 for complete `city.yaml`/`highway.yaml` fusion blocks — these are the canonical templates; `highway_cam.yaml` follows the same shape substituting `live_lane` for `road` and omitting `exclusion_zones`/`count_lines`.

### 15.5 Appendix C — draft `requirements.txt`

```
ultralytics
opencv-python
supervision
scikit-learn
numpy
scipy
shapely
pyyaml
httpx
pytest
fastapi
uvicorn[standard]
sqlalchemy
pydantic
websockets
```
(Install PyTorch/torchvision separately first, per E0-T3, using the CUDA-specific index URL — do not list a bare `torch` in this file since the correct build depends on the local driver/CUDA version detected at setup time.)

### 15.6 Appendix D — glossary

- **ICCC** — Integrated Command and Control Centre (India's Smart City program's central monitoring hub).
- **Golden hour** — the first hour after a traumatic injury, during which treatment has the highest chance of preventing death.
- **PET** — Post-Encroachment Time, a traffic-safety proxy measuring the time gap between one road user leaving a conflict point and another arriving at it; smaller PET = more dangerous near-miss.
- **ByteTrack** — a multi-object tracking algorithm that associates detections across frames into persistent track IDs, robust to brief occlusion/low-confidence detections.
- **Green corridor** — a sequence of traffic signals coordinated to turn green ahead of an approaching emergency vehicle, clearing its path.
- **DBSCAN** — Density-Based Spatial Clustering of Applications with Noise; groups nearby points into clusters without needing a predefined cluster count, used here to detect pedestrian clustering.
- **ROI** — Region of Interest; a polygon defining where a camera's analysis logic applies (e.g., the roadway, a live lane).
