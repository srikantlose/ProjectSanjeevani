# Project Sanjeevani — Progress Tracker

Read `plan.md` first. Work top-to-bottom, task by task. Tick a box the moment its acceptance check passes. Add a one-line note under a task if any threshold, config value, or approach deviated from the plan — future sessions rely on these notes to know what actually shipped vs. what was originally specced.

Epics marked **[GATE]** must fully pass their gate task's acceptance check before the next epic begins.

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
- [ ] E2-T2 — Collision signal
- [ ] E2-T3 — Stationary signal
- [ ] E2-T4 — Flow signal

## E3 — Signals (Novel) **[GATE]**
- [ ] E3-T1 — Crowd-as-signal
- [ ] E3-T2 — Rider-down heuristic
- [ ] E3-T3 — Pose confirmation + real-clip gate — **EPIC GATE: occluded clip fires `crowd`, not `collision`**

## E4 — Fusion + Evidence
- [ ] E4-T1 — Fusion module
- [ ] E4-T2 — Severity module
- [ ] E4-T3 — Ring buffer + evidence writer
- [ ] E4-T4 — Emitter with offline queue

## E5 — API Core
- [ ] E5-T1 — FastAPI app + SQLAlchemy models
- [ ] E5-T2 — Candidate endpoint + persistence
- [ ] E5-T3 — WebSocket hub
- [ ] E5-T4 — Verify endpoint + state machine skeleton
- [ ] E5-T5 — Static media + tile proxy

## E6 — Simulators
- [ ] E6-T1 — Seed data files (hospitals, ambulances, junctions)
- [ ] E6-T2 — Routing client + route prefetch
- [ ] E6-T3 — Ambulance mover
- [ ] E6-T4 — Corridor sequencer
- [ ] E6-T5 — Hospital pre-alert

## E7 — Dashboard
- [ ] E7-T1 — App shell, router, WS store
- [ ] E7-T2 — Control room — feed grid + incident cards
- [ ] E7-T3 — WhyPanel + VerifyModal
- [ ] E7-T4 — Dispatch map + ambulance animation
- [ ] E7-T5 — Corridor + hospital markers + ETA/stopwatch
- [ ] E7-T6 — Hospital console
- [ ] E7-T7 — Metrics view

## E8 — Scenario Content **[GATE]**
- [ ] E8-T1 — Dataset acquisition
- [ ] E8-T2 — Camera ROI configs for the two demo cameras
- [ ] E8-T3 — Scenario 1 — junction rider-down, occluded (end-to-end)
- [ ] E8-T4 — Scenario 2 — highway stationary vehicle (end-to-end) — **EPIC GATE: full 7-beat demo storyline runs with no manual intervention beyond video switch + Confirm taps**

## E9 — Evaluation
- [ ] E9-T1 — Eval runner
- [ ] E9-T2 — Metrics report + API wiring
- [ ] E9-T3 — Near-miss study

## E10 — Polish + Demo Insurance
- [ ] E10-T1 — Demo runbook script
- [ ] E10-T2 — Rehearsal checklist + backup video
- [ ] E10-T3 — Report skeleton fill-in
- [ ] E10-T4 (stretch, optional) — IDD fine-tuning

---

## Deviation log

*(Append one entry per deviation from the plan — new threshold values, substituted datasets, skipped stretch items, etc. Keep entries short: task ID, what changed, why.)*

- E0-T3 — Plan specified Python 3.11; only 3.13 and 3.14 were available on this machine (no 3.11 installer present), so the venv was created with Python 3.13.7. PyTorch 2.11.0+cu128 installs cleanly and `torch.cuda.is_available()` returns `True` on the RTX 4060 (driver 591.74, CUDA 13.1) — no functional impact expected. Torch/torchvision installed via `--index-url https://download.pytorch.org/whl/cu128` (cu128 build; driver's CUDA 13.1 is backward-compatible with cu128 wheels).
- E0-T4 — `npm install -D tailwindcss` pulled Tailwind v4.3.2, which replaced the v3-style `tailwind.config.js` + PostCSS + `autoprefixer` flow described in plan.md §E0-T4 with a CSS-first setup: `@tailwindcss/vite` plugin registered in `vite.config.ts`, and `src/index.css` now just has `@import "tailwindcss";` (no `tailwind.config.js`/`postcss.config.js` files exist). Verified working via `vite build` (compiled utility classes present in output CSS) and a live `vite dev` request. Also stripped the default Vite/React template's marketing content (hero image, logos, docs/social sections) from `App.tsx`/`App.css`/`assets/` since it's all replaced in E7 anyway — `App.tsx` is currently a minimal placeholder.
- E0-T4 (follow-up, 2026-07-07) — User asked to spend as little time/effort as possible on frontend/UI-UX until they provide styles/designs later. Applies to all remaining E7 dashboard tasks: build functional data-wiring only, no visual design work. Saved as a standing memory (`feedback_frontend_minimal`).
- E1-T2 — Detector/tracker wrapper needs real detectable content to verify; synthetic solid-color frames (used for E1-T1) don't produce YOLO detections. Added `tests/conftest.py::vtest_video`, a session-scoped fixture that downloads a small standard OpenCV test clip (pedestrians/cars, BSD-licensed) on demand into `tests/fixtures/` (gitignored, not committed) — same on-demand pattern as `scripts/download_models.py`. This is dev/test infra only, not part of the project's actual dataset (§6/E8). Also added `lap` to `requirements.txt` (pulled in automatically by ultralytics as a ByteTrack dependency).
