# Project Sanjeevani — Progress Tracker

Read `plan.md` first (rev. 2, 2026-07-08). Work top-to-bottom, task by task. Tick a box the moment its acceptance check passes. Add a one-line note under a task if any threshold, config value, or approach deviated from the plan — future sessions rely on these notes to know what actually shipped vs. what was originally specced.

Epics marked **[GATE]** must fully pass their gate task's acceptance check before the next epic begins. Tasks marked **USER ACTION REQUIRED** pause on the user; continue with any later task that doesn't depend on them.

---

## E0 — Scaffold
- [x] E0-T1 — Repo init & gitignore
- [x] E0-T2 — Directory scaffold
- [x] E0-T3 — Python environment + CUDA verification
- [x] E0-T4 — Vite dashboard scaffold
- [x] E0-T5 — Model download script

## E1 — Video + Detection Core
- [x] E1-T1 — Video source with real-time pacing
- [x] E1-T2 — Detector + tracker wrapper
- [x] E1-T3 — FrameContext / track-history builder
- [x] E1-T4 — Debug overlay / annotated output

## E2 — Signals (Direct)
- [x] E2-T1 — Signal base interface + synthetic test fixtures
- [x] E2-T2 — Collision signal
- [x] E2-T3 — Stationary signal
- [x] E2-T4 — Flow signal

## E3 — Signals (Novel)
- [x] E3-T1 — Crowd-as-signal
- [x] E3-T2 — Rider-down heuristic
- [x] E3-T3 (revised) — Pose confirmation, stub-injected tests + real-model smoke *(the occluded-clip gate moved to E8-T3/GATE-A)*

## E4 — Fusion + Evidence + Engine wiring
- [x] E4-T0 — Config system (config.py, signal_factory.py, mode YAMLs, signal kwargs refactor, pytest.ini)
- [x] E4-T1 — Fusion module (weighted sum, overrides, cooldown grid, IncidentCandidate)
- [x] E4-T2 — Severity module
- [x] E4-T3 — Evidence buffer (ring buffer, clip + snapshot, ffmpeg re-encode w/ fallback)
- [x] E4-T4 — Emitter with offline queue
- [x] E4-T5 — Engine integration (vtest highway config acceptance, no new data needed)

## E5 — API Core
- [x] E5-T1 — App + models + CORS + seed-on-startup
- [x] E5-T2 — Candidate endpoint + persistence
- [x] E5-T3 — WebSocket hub
- [x] E5-T4 — Verify endpoint + state machine (dispatch stub)
- [x] E5-T5 — Media mounts + tile proxy

## E6 — Simulators
- [x] E6-T1 — Seed files (pinned §9.1 values) + junctions script + startup load
- [x] E6-T2 — Routing client + geo helpers + route prefetch (26 committed GeoJSONs)
- [x] E6-T3 — Ambulance mover (replaces E5-T4 stub)
- [x] E6-T4 — Corridor sequencer
- [x] E6-T5 — Hospital pre-alert

## E7 — Dashboard (MINIMAL UI ONLY — no styling/design; that is E10-T5)
- [x] E7-T1 — Shell, router, types, store, ws, api helpers
- [x] E7-T2 — FeedGrid + IncidentFeed
- [x] E7-T3 — WhyPanel + VerifyModal
- [x] E7-T4 — Dispatch map + ambulance tween + route line
- [x] E7-T5 — Corridor circles + EtaBanner + Stopwatch
- [ ] E7-T6 — Hospital console
- [ ] E7-T7 — Metrics view

## E8 — Scenario Content **[GATE-A and GATE-B live here]**
- [ ] E8-T0 — ROI annotation tool (scripts/annotate_roi.py)
- [ ] E8-T1 — Dataset acquisition — **USER ACTION REQUIRED** (docs/data_checklist.md + make_clips.py + manifest ≥15 rows)
- [ ] E8-T2 — Demo camera configs + scenario YAMLs (placeholder occluded clip; swap later is config-only)
- [ ] E8-T3 — Scenario 1 end-to-end — **GATE-A: crowd ≥0.5 while collision <0.9 on the occluded clip; fusion fires; DISPATCHED with one Confirm**
- [ ] E8-T4 — Scenario 2 end-to-end — **GATE-B: full 7-beat demo, both scenarios back-to-back, no manual intervention beyond engine start + Confirm taps**

## E9 — Evaluation
- [ ] E9-T1 — Eval runner (needs E8-T1 data)
- [ ] E9-T2 — Metrics API + dashboard wiring
- [ ] E9-T3 — Near-miss study (public long-form footage per user decision 2026-07-08)

## E10 — Polish + Demo Insurance
- [ ] E10-T1 — Preflight script + run_demo.ps1
- [ ] E10-T2 — Rehearsal checklist + backup video
- [ ] E10-T3 — Report skeleton + future-work doc fill-in
- [ ] E10-T4 (stretch, optional) — IDD fine-tuning
- [ ] E10-T5 — Styling pass — **BLOCKED ON USER design specs**

---

## Deviation log

*(Append one entry per deviation from the plan — new threshold values, substituted datasets, skipped stretch items, etc. Keep entries short: task ID, what changed, why.)*

- E7-T5 — Added `GET /api/junctions` (new file `services/api/routers/junctions.py`, wired into `main.py`), not in the original E7-T5 file list, because the `corridor.updated` WS payload (`{dispatch_id, junction_id, junction_name, signal_state}`) carries no lat/lon — the dashboard has no other way to place a corridor marker on the map. Mirrors the existing `hospitals.py`/`ambulances.py` router pattern exactly. `MapView` fetches it once and renders a small pill-labeled marker (text = signal state) only for junction IDs actually present in the store's `corridor` record, not all 40 seeded junctions.
  - **Finding worth flagging for E8 tuning, not fixed now**: live-verified the real `/api/incidents/candidate` -> confirm -> dispatch flow against the real seeded data (Trinity Circle incident, real OSRM route) and computed offsets from that real route to all 40 seeded junctions — the *nearest* one was 285m away, well outside `CorridorController`'s `PROXIMITY_M = 30.0` (services/api/sim/corridor.py). With only 40 sparsely-sampled OSM signal nodes across the whole Bengaluru bbox, a real dispatch route may never pass within 30m of any of them, so the green-corridor effect could be invisible in the actual demo unless the two demo scenarios (E8-T3/T4) are deliberately routed past a junction that's genuinely on the seeded list, or `PROXIMITY_M`/junction sampling density is revisited in E8. To verify the frontend wiring itself (the actual scope of E7-T5) without waiting out this route's ~640s real-time ETA, `PROXIMITY_M` was temporarily bumped to 3000.0, the backend restarted, and a fresh dispatch run observed live in a browser: 5 junction markers appeared labeled "GREEN", then correctly flipped to "DEFAULT" one by one ~10s after the ambulance passed each (per `REVERT_DELAY_S`), while the stopwatch froze at DISPATCHED and the ETA banner counted down live. `PROXIMITY_M` was reverted to `30.0` immediately after (confirmed via full `82 passed` pytest run) — this was a verification-only change, not a permanent calibration decision.
- E7-T4 — **Bug caught by live-testing, not by the pytest suite**: `incident_to_payload` (used by `GET /api/incidents` and `GET /api/incidents/{id}`) never included dispatch info -- only the one-time `incident.updated` WS broadcast at the moment of confirmation carried the `dispatch` object. A dashboard client that loads or refreshes via REST *after* a dispatch already happened (the exact sequence my E7-T4 Playwright script used: POST candidate, confirm, *then* navigate to `/dispatch`) got an incident with `status: "DISPATCHED"` but no ambulance/hospital/route info at all, so the map never rendered anything. Fixed by adding `_dispatch_payload()` (queries the incident's `dispatches` relationship + the `Hospital` table, same shape as the WS payload) and including it in `incident_to_payload` whenever a dispatch exists. Added a regression test (`test_dispatch_info_survives_a_rest_reload_after_confirm`) since none of the existing WS-connected tests would have caught this (they all stayed connected across the confirm call, same as the demo's actual real-time usage — only a reload-after-the-fact exposes the gap). Live-verified afterward: real Bengaluru map tiles, route line, and all three markers (blue=incident, green=hospital, red=ambulance) render correctly, with the ambulance marker's DOM transform genuinely changing position between two observations 2.5s apart.
- E7-T3 — Live-verified in a real browser: posted a candidate, clicked its card, confirmed all 4 `<progress>` bars match the posted signal scores exactly (0.20/0.95/0.80/0.40), clicked Confirm, watched status flip PENDING_VERIFICATION -> DISPATCHED live with no page reload, and confirmed the VerifyModal correctly disappears once no longer pending. This incidentally re-exercised the full E6 dispatch chain through the real UI (nearest-ambulance selection, routing) with zero console errors.
- E7-T1 — Live-verified in a real browser (Playwright/Chromium via npx, since `chromium-cli` from the `run` skill isn't installed on this Windows machine — used the skill's documented fallback pattern instead) rather than just `tsc`/`vite build`: all 4 routes render their heading, and `ws:` status flips from `connecting` to `open` within ~1s of the API being up. First run showed 2 transient `fetchIncidents` "Failed to fetch" console errors on cold Vite start; a second run against the now-warm Vite dep cache showed zero errors, confirming it was Vite's documented dependency-pre-bundling page-reload behavior on first request, not an app bug.
- E6-T3/T4/T5 — Built together in one pass rather than strictly sequentially: per plan.md §9.3, the mover's `dispatch_incident` calls `hospital.select_hospital` (E6-T5) and `run_dispatch`'s per-tick speed calc calls `corridor.speed_multiplier` (E6-T4) — the mover cannot function, let alone be tested, without both. `sim/hospital.py` and `sim/corridor.py` were built in full (not stubbed) as part of this pass; E6-T5's own listed deliverable (`tests/test_sim_hospital.py`, selection-rule coverage incl. the 1.5x trauma-preference bound) was still written as its own dedicated test file, same for E6-T4's `tests/test_sim_corridor.py`.
  - **Bug caught by testing**: `run_dispatch` is a fire-and-forget background task (`asyncio.create_task`) that outlives the HTTP request, so it originally imported the global `SessionLocal` from `db.py` directly — in tests (and in general) that's the wrong engine, since the request's `db` session came from `app.dependency_overrides[get_db]` pointing at an isolated tmp DB. Fixed by deriving `session_factory = sessionmaker(bind=db.get_bind())` in `dispatch_incident` and threading it through to `run_dispatch`, so the background task always binds to the same engine the request used.
  - **Bug caught by testing**: `_drive_leg` originally used `tick_interval_s` for *both* the real `asyncio.sleep` duration *and* the simulated distance covered per tick (`traveled += speed * tick_interval_s`). The two effects cancel out algebraically — total wall-clock time to finish a leg is `total_dist / speed` regardless of `tick_interval_s` — so passing a small value for tests wouldn't have sped anything up. Fixed by decoupling: distance-per-tick now always uses a fixed `SIMULATED_SECONDS_PER_TICK = 1.0` (real 1 Hz ticks, matching the brief's own "1 Hz ticks" language), while `tick_interval_s` purely controls the real sleep duration (and the `SCENE_DWELL_S` scaling). A 2km leg now takes ~206 ticks regardless of speed setting, but at `tick_interval_s=0.005` those ticks fly by in ~1s of real time instead of ~206s.
  - `project_distance`'s nearest-*vertex* approximation (plan.md §9.2, explicitly called out as acceptable) only works when the polyline is densely sampled — real OSRM routes are (E6-T2 found ~1 vertex per 27m on an 8.7km route), but a naive 2-point synthetic test line puts any midpoint junction ~1km from the "nearest vertex" and fails corridor selection entirely. `test_sim_corridor.py` uses a 100-point densified line to match real-route density; noted here so a future synthetic-route test doesn't rediscover this the hard way.
  - Live-verified end-to-end against the real running API (not just unit tests): confirmed a real posted candidate, watched `ambulance.position` tick at ~1 Hz over `/ws`, confirmed nearest-ambulance selection picked `amb_04` (genuinely nearest to Trinity Circle per the E6-T2 prefetch distances) and per-tick displacement matched 35 km/h (~9.7 m/s) exactly.
- E6-T2 — Coordinate-based cache-key matching (rounding lat/lon to 4dp against a registry, per plan.md §9.2) is ambiguous by construction: ambulances are seeded at their home hospital's exact coordinates (e.g. `amb_01` and `hosp_01`/NIMHANS share 12.9430,77.5960), so a single "first match wins" lookup could resolve a coordinate to the wrong id and miss an existing cache file. Fixed `_match_id` -> `_match_ids` (returns every id whose coordinates match, not just one) and `_load_cached_route` tries every `(from_id, to_id)` candidate pair until an existing file is found. Caught immediately by `test_get_route_falls_back_to_cache_when_osrm_unreachable`, which failed on the first implementation. All 26 routes were fetched live from the real OSRM public server (not synthetic) and committed under `data/routes/`.
- E6-T1 — Live Overpass query initially failed with `406 Not Acceptable` (confirmed via direct `curl` too, so not an httpx quirk) — the public Overpass instance now requires an explicit `Accept: application/json` header (and a `User-Agent`) rather than accepting curl/httpx's bare defaults. Added both headers to `scripts/seed_junctions.py`'s request; the live query then succeeded and returned real junction nodes (40, sampled from the full result set), so `data/seed/junctions.json` contains genuine OSM data rather than the hand-curated fallback list. Verified end-to-end: fresh DB startup loads 8 hospitals, 5 ambulances, 40 junctions.
- E5-T5 — Verified the tile proxy against the real OpenStreetMap tile server (not just the monkeypatched unit tests): `GET /tiles/12/1315/2607.png` fetched a genuine 256x256 PNG on first request, cached it to `data/tile_cache/12/1315/2607.png`, and served byte-identical content on a second request. `data/clips` and `data/processed` are created with `mkdir(parents=True, exist_ok=True)` before the `StaticFiles` mounts so a fresh checkout (where `data/clips` is gitignored and doesn't exist yet) doesn't fail app startup.
- E5-T1 — Built `routers/hospitals.py` and `routers/ambulances.py` (simple list-all endpoints) as part of this task rather than a later one: no task in §13 explicitly claims them, but E5-T1's own acceptance check (`GET /api/hospitals` returns `[]`) requires them to exist. Verified manually: `uvicorn services.api.main:app` starts clean, `sqlite3`-equivalent check (via Python's `sqlite3` module — the `sqlite3` CLI isn't installed on this machine) shows all 7 tables, `GET /api/hospitals`/`/api/ambulances` both return `[]` with seed files absent (warning logged, no crash), and CORS preflight to `http://localhost:5173` returns the expected `access-control-allow-origin` header. For future test files (E5-T2+): DB isolation will use FastAPI's `app.dependency_overrides[get_db]` pattern (a tmp-path engine/session substituted per test) rather than the `SANJEEVANI_DB_PATH` env var, since the env var is only read once at module-import time and a later test file can't un-cache that — the dependency-override approach is the standard, robust way to isolate FastAPI+SQLAlchemy tests and doesn't fight Python's module caching.
- E4-T5 — `set_current_frame_image` had only ever been defined on `RiderDownSignal` (added ad hoc in E3-T3), not on the shared `Signal` base class as plan.md §7.2 specifies ("base-class no-op hook"). Wiring the engine to call it on every signal (`CollisionSignal`, `StationarySignal`, `FlowSignal`, `CrowdSignal` included) raised `AttributeError` immediately — caught by the new engine-integration tests. Fixed by moving the no-op to `Signal.set_current_frame_image` in `signals/base.py` and removing the now-redundant override from `RiderDownSignal` (it inherits the no-op; only `PoseConfirmedRiderDownSignal` still overrides it meaningfully).
- E4-T5 — `run()` gained three parameters beyond the plan.md §7.8 signature to keep tests from writing into the real project directories: `evidence_out_root` (default `"data/clips"`), `queue_path` (default `"data/queue/pending_incidents.jsonl"`), `start_retry_thread` (default `True`, threaded to `Emitter`). Defaults match the spec exactly for real CLI usage; tests pass tmp_path-based overrides. Verified the literal CLI acceptance check for real: `python -m services.detection.engine --camera configs/cameras/vtest_highway_test.yaml --headless --speed-factor 20` produced 4 candidates, all with `stationary` in `[0.85, 0.9]`, each with a decodable `evidence.mp4` + `snapshot.jpg` under `data/clips/` (cleaned up after verifying, since that directory is gitignored/regenerated).
- E4-T3 — ffmpeg is already installed on this machine at `/c/ffmpeg/ffmpeg` (on PATH), so no `winget install Gyan.FFmpeg` step was needed. Both the ffmpeg-present and ffmpeg-absent (monkeypatched `shutil.which`) code paths in `EvidenceBuffer` were exercised and pass.
- E3-T3 — `_default_pose_checker`'s keypoint math (`np.linalg.norm`, `np.dot`, `np.array` vertical) failed on `keypoints.xy[0]` directly: Ultralytics returns keypoints as a CUDA tensor when the pose model runs on GPU, and numpy ops can't consume a CUDA tensor without an explicit transfer. Fixed with `keypoints.xy[0].cpu().numpy()`. Caught immediately by the real-model smoke test (`test_default_pose_checker_smoke_on_real_upright_person`) — exactly the kind of bug synthetic-only fixtures can't catch, which is why that smoke test exists per plan.md §7.2/E3-T3.
- 2026-07-08 — **Plan rev. 2**: full codebase review; restructured E3-T3→E10 with detailed contracts (config system E4-T0, engine integration E4-T5, CORS, pinned seed data, minimal-UI E7, ROI tool task E8-T0, user-checklist data policy). User decisions captured: datasets via script+checklist; occluded demo clip = placeholder now/staged later; near-miss study on public footage. Occluded-clip gate moved from E3-T3 to E8-T3 (GATE-A) since the footage only exists after E8-T1.
- E3-T2 — Rider-down's vehicle-confirmation check originally re-tested "is the vehicle's velocity dropping *right now*" at the moment the 2s sustained-fall duration gate is satisfied — but that moment is, by construction, ~2s+ after the actual impact, so the live velocity-drop window (0.5s lookback) had long since gone quiet, and the signal never fired (caught by the acceptance test itself). Fixed by recording each vehicle's impact-signature timestamp once (`_vehicle_last_event_ts`) when a velocity-drop or aspect-change is observed, then checking that stored event time falls within `EVENT_CORRELATION_WINDOW_S=3.0`s of the person's fall onset (`lying_since`), rather than re-checking a live rolling window at confirmation time. Same class of timing bug as the E2-T2 collision-signal fix, now understood as a general pattern: any "confirm later" check needs to reference a stored event timestamp, not a live short-window recheck.
- E3-T1 — Crowd signal's formation-rate check appends a cluster-membership observation *every frame* (using an empty set when no valid DBSCAN cluster exists that frame), rather than only appending when a cluster is found. This makes "new members vs. 8s ago" well-defined even when the cluster is forming from scratch (0 members 8s ago -> N members now), which is the actual demo scenario (bystanders converging where no crowd existed a moment before). Appending only on successful clustering (a more literal first reading of §7.4) breaks this case: the first frame a cluster becomes detectable already requires >=min_samples=4 mutually-close people, so an all-at-once-arriving group of exactly 5 would already show only 1 "new" member relative to the first (self-same) observation. Net behavior matches spec intent: fires on fresh crowd formation, does not fire on an already-stable clustered group.
- E2-T2 — Collision signal's confirmation timing: §7.4 describes the stationary-confirmation as happening "within 3s" of the overlap+velocity-drop event. Velocity is smoothed over a 5-frame window (tracker_ctx), so a real deceleration-to-zero takes a few frames to read as fully stationary — that lag stacked with the 3s stationary-duration requirement can exceed a literal 3s deadline. Implemented `PENDING_EXPIRY_S = 15.0` (generous cleanup timeout) while keeping the actual physical requirement `STATIONARY_DURATION_S = 3.0` from spec. Net effect on behavior: unchanged (still requires overlap/near-contact + sudden velocity change + 3s of subsequent rest before escalating 0.6→0.95), just not hard-cut at exactly 3 wall-clock seconds.
- E1-T2 — Detector/tracker wrapper needs real detectable content to verify; synthetic solid-color frames (used for E1-T1) don't produce YOLO detections. Added `tests/conftest.py::vtest_video`, a session-scoped fixture that downloads a small standard OpenCV test clip (pedestrians/cars, BSD-licensed) on demand into `tests/fixtures/` (gitignored, not committed) — same on-demand pattern as `scripts/download_models.py`. This is dev/test infra only, not part of the project's actual dataset (§6/E8). Also added `lap` to `requirements.txt` (pulled in automatically by ultralytics as a ByteTrack dependency).
- E0-T4 (follow-up, 2026-07-07) — User asked to spend as little time/effort as possible on frontend/UI-UX until they provide styles/designs later. Applies to all remaining E7 dashboard tasks: build functional data-wiring only, no visual design work. Saved as a standing memory (`feedback_frontend_minimal`).
- E0-T4 — `npm install -D tailwindcss` pulled Tailwind v4.3.2, which replaced the v3-style `tailwind.config.js` + PostCSS + `autoprefixer` flow described in the original plan with a CSS-first setup: `@tailwindcss/vite` plugin registered in `vite.config.ts`, and `src/index.css` now just has `@import "tailwindcss";` (no `tailwind.config.js`/`postcss.config.js` files exist). Verified working via `vite build` (compiled utility classes present in output CSS) and a live `vite dev` request. Also stripped the default Vite/React template's marketing content (hero image, logos, docs/social sections) from `App.tsx`/`App.css`/`assets/` since it's all replaced in E7 anyway — `App.tsx` is currently a minimal placeholder.
- E0-T3 — Plan specified Python 3.11; only 3.13 and 3.14 were available on this machine (no 3.11 installer present), so the venv was created with Python 3.13.7. PyTorch 2.11.0+cu128 installs cleanly and `torch.cuda.is_available()` returns `True` on the RTX 4060 (driver 591.74, CUDA 13.1) — no functional impact expected. Torch/torchvision installed via `--index-url https://download.pytorch.org/whl/cu128` (cu128 build; driver's CUDA 13.1 is backward-compatible with cu128 wheels).
