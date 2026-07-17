# Data acquisition checklist (E8-T1)

**USER ACTION REQUIRED.** None of the sources below can be downloaded by a script
end-to-end: each one gates behind either a Google Drive folder (which requires a
signed-in browser click-through, not a scriptable URL) or a free account +
manual acceptance of academic-use terms. This doc is the precise list of what
to fetch and where to put it; once files land under `data/raw/<source>/`,
`scripts/make_clips.py` does the rest automatically.

URLs below were verified live on 2026-07-17. Re-check before using if this
doc is read much later — academic dataset hosting moves around.

## Pipeline once files are on disk

```
venv\Scripts\python.exe scripts\make_clips.py --src data/raw/<source> --out data/processed
```

This re-encodes everything in `data/raw/<source>/` to 1280x720/25fps/H.264
crf23 and writes `data/processed/<source>_0001.mp4`, `<source>_0002.mp4`, ...
(plan.md §6.3). After that, add one row per usable clip to
`data/manifests/eval_manifest.csv` (header already in place):

```
clip_path,scenario_type,gt_label,gt_event_time_s,camera_config,notes
```

- `gt_label`: 1 for a clip containing the event, 0 for a clean negative.
- `gt_event_time_s`: seconds into the *processed* clip where the event starts; blank for negatives.
- `scenario_type`: one of `city_collision`, `city_riderdown_occluded`, `city_crowd_only`, `city_negative`, `highway_stationary`, `highway_negative` (add new ones freely; anything ending `_occluded` feeds E9-T1's occlusion-robustness metric).
- `camera_config`: which `configs/cameras/*.yaml` this clip should be evaluated against (usually `junction_cam.yaml` for city-style CCTV angles, `highway_cam.yaml` for elevated/overpass angles).
- `notes`: anything a grader/reader would want to know (source, whether staged, occlusion description).

## Pause point

`E8-T3`/`E9-T1` need the manifest to have **≥ 15 rows spanning ≥ 2 positive
`scenario_type`s plus some negatives** before they can run. Until then, work
can continue on anything not touching real footage (E8-T2's config scaffolding,
E10 tooling, etc.) — see PROGRESS.md for exactly what's blocked vs. not.

---

## 1. CADP — CCTV traffic-accident clips (primary positives)

**What:** ~1,400 real CCTV-angle accident clips (205 with full spatio-temporal
annotation) collected from YouTube by Shah et al., ACM MM 2018/2019 (arXiv
1809.05782). CCTV framing is the closest public match to this project's
fixed junction-camera setup, so this is the best source for
`city_collision` / `city_riderdown_occluded` rows.

**Access:** project page —
[ankitshah009.github.io/accident_forecasting_traffic_camera](https://ankitshah009.github.io/accident_forecasting_traffic_camera).
The page links a "Dataset Release README" plus Google Drive folders for the
extracted frames and an externally-hosted annotations JSON. No account
signup is required, but Drive's own "download anyway" click-through applies
to the larger folders. Non-commercial/research-use-only per the page; do not
redistribute.

**Steps:**
1. Open the project page above, follow the "Dataset Release README" link and read it once — it explains which of the two file sets (full frames vs. video segments) you actually want. We want **video segments**, not the pre-extracted-frame set, since `make_clips.py` re-encodes whole video files.
2. Download the video segments to `data/raw/cadp/`.
3. Skim titles/thumbnails for a handful of two-wheeler-involved accidents (for `city_riderdown_occluded`) and general vehicle-vehicle collisions (for `city_collision`) — CADP does not pre-label by vehicle type, so this is a manual eyeball pass over maybe 20-30 candidates to find 5-8 usable ones.

## 2. UCF-Crime — `RoadAccidents` category (secondary positives)

**What:** Real-world surveillance-camera anomaly dataset (Sultani et al.,
CVPR 2018); one of its 14 categories, `RoadAccidents`, is exactly the traffic
collision footage we want, in CCTV framing similar to CADP.

**Access:** the authoritative host is
`https://www.crcv.ucf.edu/data1/chenchen/UCF_Crimes.zip`, but that .zip is
the **entire** 14-category dataset (100+ GB) — too large just for one
category. Easier: the Kaggle mirror
[kaggle.com/datasets/odins0n/ucf-crime-dataset](https://www.kaggle.com/datasets/odins0n/ucf-crime-dataset)
splits videos into per-category folders including `RoadAccidents/`, so you
can download just that folder. Kaggle requires a free account and (for CLI
download) an API token generated from your Kaggle account settings page —
that one-time signup is the "user action" here; after that,
`kaggle datasets download odins0n/ucf-crime-dataset -f <path-to-RoadAccidents-file>`
is scriptable.

**Steps:**
1. Create a free Kaggle account if you don't have one; generate an API token (Account → Settings → Create New Token), which drops a `kaggle.json` into `~/.kaggle/`.
2. Download just the `RoadAccidents` subfolder's videos to `data/raw/ucf_crime_road_accidents/`.
3. UCF-Crime's own labeling is coarse (anomaly present somewhere in a long video, not per-frame) — for the manifest's `gt_event_time_s`, you'll need to scrub each clip once to note roughly where the accident happens.

## 3. CCD (CarCrashDataset, Cogito2012) — dashcam positives + negatives

**What:** 1,500 dashcam crash clips + 3,000 dashcam normal-driving clips
(Bao et al., ACM MM 2020). Dashcam framing (not fixed CCTV) is a worse match
to our junction camera, but it's the easiest source of clean **negative**
clips (the 3,000 "Normal" videos), and the crash clips are useful
robustness/false-negative checks even if not framing-matched.

**Access:**
[github.com/Cogito2012/CarCrashDataset](https://github.com/Cogito2012/CarCrashDataset) →
Google Drive folder at
`https://drive.google.com/drive/folders/1NUwC-bkka0-iPqhEhIgsXWtj0DA2MR-F`.
No registration required beyond the Drive click-through; used for research
per the repo's terms.

**Steps:**
1. From the Drive folder, grab `videos/Crash-1500/` (a sample of ~10-15 is enough, not all 1,500) and `videos/Normal/` (similarly, a sample of ~10-15) into `data/raw/ccd_crash/` and `data/raw/ccd_normal/` respectively — two separate source dirs since `make_clips.py` names files by source-directory.
2. `Crash-1500.txt` in that same folder has per-video temporal accident-onset annotations — useful for filling in `gt_event_time_s` without re-scrubbing by eye.

## 4. DoTA — driving-video anomalies (false-alarm tuning, optional)

**What:** 4,677 dashcam clips with categorized anomalies (collisions,
off-road, oncoming, pedestrian, etc.) — useful for false-alarm-rate tuning
against near-miss/anomaly types that aren't full collisions, but the full
extracted-frames download is ~55 GB.

**Access:**
[github.com/MoonBlvd/Detection-of-Traffic-Anomaly](https://github.com/MoonBlvd/Detection-of-Traffic-Anomaly) —
Google Drive links in the README, split into five 10 GB + one 5 GB zip for
easier downloading. No registration beyond Drive click-through.

**Priority:** lowest of the four positive sources — only pull this if the
manifest is short on `_negative`/false-alarm rows after CADP/UCF-Crime/CCD.
A handful of clips (not the full 55 GB) is plenty; grab whichever of the
split zips is smallest, extract, and pull 5-10 clips into `data/raw/dota/`.

---

## 5. Long-form footage for the near-miss study (E9-T3)

**Recommended: UA-DETRAC.** 10 hours of real fixed-camera traffic (overpass
cameras in Beijing/Tianjin, 24 locations, 100 sequences, 25fps @ 960x540),
Wen et al./Lyu et al., CVIU 2020. This is a **non-Bengaluru** public dataset
(per the standing decision to allow that, honestly labeled in the report),
but it's the best fit for the near-miss conflict study specifically because
it's genuinely fixed-camera CCTV-style footage of real dense mixed traffic —
closer to our actual use case than a dashcam dataset, and unlike a scraped
live YouTube stream it's a citable, reproducible academic source.

**Access:** official page
[sites.google.com/view/daweidu/projects/ua-detrac](https://sites.google.com/view/daweidu/projects/ua-detrac) or the Kaggle mirror
[kaggle.com/datasets/bratjay/ua-detrac-orig](https://www.kaggle.com/datasets/bratjay/ua-detrac-orig)
(same Kaggle account/API token as UCF-Crime above covers this too, if you go
that route).

**Steps:**
1. **Please confirm this choice** (or name a different long-form source you'd rather use) before E9-T3 runs against it — per the original data-sourcing decision, the near-miss footage source needs your sign-off, not just mine.
2. If approved: download 2-3 of the longest available sequences (several are 1-2 minutes each in the public release; concatenating several sequences from the *same* camera location gives a longer continuous analysis window) into `data/raw/ua_detrac/`.
3. `eval/near_miss/conflicts.py` (built in E9-T3) runs directly against whatever lands in `data/processed/` after `make_clips.py` — no manifest row needed for this one, it's a separate study, not part of `eval_manifest.csv`.

---

## 6. Occluded rider-down demo clip (the GATE-A centerpiece)

Per the earlier decision: build and pass GATE-A now against the **best
available placeholder**, and swap in a purpose-shot clip later — swapping is
a one-line change (`configs/cameras/junction_cam.yaml: source_video`) plus
one manifest row, nothing structural.

**What to look for:** among the CADP / UCF-Crime `RoadAccidents` clips
you've already pulled for §1/§2 above, find one two-wheeler-down accident
where the fallen rider is **partially occluded** for at least part of the
clip (by another vehicle, a crowd, or camera angle) — this is what exercises
the pose-confirmation boost (`rider_down.py`'s `PoseConfirmedRiderDownSignal`)
under realistic conditions rather than a clean unobstructed fall. This can't
be scripted (no dataset tags "occluded"); it's a ~10-clip eyeball pass over
whatever two-wheeler accidents came back from §1/§2.

**If nothing suitable turns up:** fall back to any clean (non-occluded)
rider-down clip for now, note `notes=placeholder, not occluded` in the
manifest row, and flag it back to me — GATE-A's acceptance bar
(`crowd ≥ 0.5` while `collision < 0.9`) still needs an actual occlusion-like
scene to be meaningful, so a fully clean clip is a weaker placeholder than an
occluded one but still lets the pipeline be smoke-tested end-to-end.

---

## 7. IDD (India Driving Dataset) — stretch only, E10-T4

Only needed for the optional fine-tuning stretch task. Academic registration
required at [idd.insaan.iiit.ac.in](https://idd.insaan.iiit.ac.in/). **Do not
prioritize this until E8/E9 are done and E10-T4 is actually being started.**

---

## What's blocking right now

As of this checklist being written, `data/raw/` and `data/manifests/eval_manifest.csv`
are empty (header only) — nothing above has been downloaded yet, since every
source needs at least one manual step (Drive click-through or Kaggle
signup). **Nothing can proceed on E8-T3 (GATE-A), E8-T4 (GATE-B), or E9-T1
(eval runner) until:**
1. At least CADP and/or UCF-Crime `RoadAccidents` clips are downloaded and processed (for `city_collision` / `city_riderdown_occluded` positives).
2. At least one occlusion-appropriate rider-down clip is identified per §6 above (or the clean-clip fallback is accepted).
3. Some negatives exist (CCD's `Normal` folder is the fastest path).
4. The manifest has ≥ 15 rows total spanning ≥ 2 positive `scenario_type`s.
5. The UA-DETRAC near-miss source (§5) is confirmed or replaced.

Everything else in E8 that doesn't need real footage (camera/scenario YAML
scaffolding, config wiring) can and will continue in parallel.
