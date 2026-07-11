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
- [ ] E6-T3 — Ambulance mover (replaces E5-T4 stub)
- [ ] E6-T4 — Corridor sequencer
- [ ] E6-T5 — Hospital pre-alert

## E7 — Dashboard (MINIMAL UI ONLY — no styling/design; that is E10-T5)
- [ ] E7-T1 — Shell, router, types, store, ws, api helpers
- [ ] E7-T2 — FeedGrid + IncidentFeed
- [ ] E7-T3 — WhyPanel + VerifyModal
- [ ] E7-T4 — Dispatch map + ambulance tween + route line
- [ ] E7-T5 — Corridor circles + EtaBanner + Stopwatch
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
