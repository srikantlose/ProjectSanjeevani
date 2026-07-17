"""Crowd-as-signal detection — the project's primary novel contribution (plan.md §7.4).

Detects sudden bystander clustering on the carriageway: a formation-rate check
(cluster gains >= FORMATION_GROWTH_THRESHOLD new members within FORMATION_WINDOW_S)
gated further by a settling check (has the cluster actually stopped moving, as
opposed to e.g. a crosswalk's worth of pedestrians who spatially cluster and
grow in count while they walk through at a steady pace) and a convergence check
(are the new members' walking directions actually converging on the cluster,
as opposed to e.g. a stable queue of people who happen to be standing/walking
near each other). This is what fires when the crash itself is occluded but
bystanders react to it -- and the settling check is what tells "bystanders
stopped to look" apart from "pedestrians crossing the road", both of which
look identical to a pure spatial-clustering-plus-growth check.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point, Polygon
from sklearn.cluster import DBSCAN

from services.detection.signals.base import Signal, SignalResult
from services.detection.tracker_ctx import FrameContext, TrackState

DBSCAN_EPS_PX = 40.0
DBSCAN_MIN_SAMPLES = 4
FORMATION_WINDOW_S = 8.0
FORMATION_GROWTH_THRESHOLD = 4
SETTLED_SPEED_PX = 5.0
CONVERGENCE_COS_THRESHOLD = 0.5
FORMATION_ONLY_SCORE = 0.5
CONFIRMED_SCORE = 0.8


@dataclass
class _ClusterObservation:
    timestamp_s: float
    member_track_ids: frozenset


class CrowdSignal(Signal):
    name = "crowd"

    def __init__(
        self,
        road_polygon: list[tuple[float, float]] | None = None,
        exclusion_zones: list[list[tuple[float, float]]] | None = None,
        eps_px: float = DBSCAN_EPS_PX,
        min_samples: int = DBSCAN_MIN_SAMPLES,
        formation_window_s: float = FORMATION_WINDOW_S,
        formation_growth_threshold: int = FORMATION_GROWTH_THRESHOLD,
        settled_speed_threshold: float = SETTLED_SPEED_PX,
        convergence_cos_threshold: float = CONVERGENCE_COS_THRESHOLD,
        formation_only_score: float = FORMATION_ONLY_SCORE,
        confirmed_score: float = CONFIRMED_SCORE,
    ):
        self._road_polygon = Polygon(road_polygon) if road_polygon else None
        self._exclusion_zones = [Polygon(z) for z in (exclusion_zones or [])]
        self.eps_px = eps_px
        self.min_samples = min_samples
        self.formation_window_s = formation_window_s
        self.formation_growth_threshold = formation_growth_threshold
        self.settled_speed_threshold = settled_speed_threshold
        self.convergence_cos_threshold = convergence_cos_threshold
        self.formation_only_score = formation_only_score
        self.confirmed_score = confirmed_score
        self._history: deque = deque()
        self._first_seen_centroid: dict[int, tuple[float, float]] = {}

    def _eligible(self, centroid: tuple[float, float]) -> bool:
        if self._road_polygon is not None and not self._road_polygon.contains(Point(centroid)):
            return False
        return not any(zone.contains(Point(centroid)) for zone in self._exclusion_zones)

    def _find_largest_cluster(self, person_tracks: list[TrackState]) -> list[TrackState]:
        if len(person_tracks) < self.min_samples:
            return []
        coords = np.array([t.centroid for t in person_tracks])
        labels = DBSCAN(eps=self.eps_px, min_samples=self.min_samples).fit_predict(coords)
        cluster_labels = [label for label in set(labels) if label != -1]
        if not cluster_labels:
            return []
        best = max(cluster_labels, key=lambda label: int(np.sum(labels == label)))
        idx = np.where(labels == best)[0]
        return [person_tracks[i] for i in idx]

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        ts = frame_ctx.timestamp_s
        result = SignalResult()

        person_tracks = [t for t in frame_ctx.tracks.values() if t.cls == "person" and self._eligible(t.centroid)]
        cluster_members = self._find_largest_cluster(person_tracks)
        member_ids = frozenset(t.track_id for t in cluster_members)

        for t in cluster_members:
            self._first_seen_centroid.setdefault(t.track_id, t.centroid)
        for stale_id in set(self._first_seen_centroid) - member_ids:
            del self._first_seen_centroid[stale_id]

        self._history.append(_ClusterObservation(timestamp_s=ts, member_track_ids=member_ids))
        while self._history and ts - self._history[0].timestamp_s > self.formation_window_s:
            self._history.popleft()

        if not member_ids:
            return result

        baseline_ids = self._history[0].member_track_ids
        new_members = member_ids - baseline_ids
        if len(new_members) < self.formation_growth_threshold:
            return result

        mean_speed = sum(math.hypot(*t.velocity) for t in cluster_members) / len(cluster_members)
        if mean_speed > self.settled_speed_threshold:
            # spatially clustered and growing, but still moving at a walking pace --
            # e.g. pedestrians crossing at a crosswalk, not bystanders who stopped.
            return result

        score = self.formation_only_score
        reasons = [
            f"crowd: cluster grew by {len(new_members)} members within {self.formation_window_s:.0f}s "
            f"and settled (mean speed {mean_speed:.1f})"
        ]

        # Convergence is checked against each new member's *net displacement since
        # they first entered the cluster*, not their current velocity -- by the
        # time a member passes the settling gate above, their instantaneous
        # velocity has typically already decayed to ~0, which would make a
        # current-velocity check vacuous. Net displacement direction still shows
        # whether they approached from a genuinely different direction (a crash
        # drawing bystanders in) rather than merely joining the back of an
        # existing static queue.
        cluster_centroid = np.mean([t.centroid for t in cluster_members], axis=0)
        cos_sims = []
        for t in cluster_members:
            if t.track_id not in new_members:
                continue
            first_seen = self._first_seen_centroid.get(t.track_id, t.centroid)
            approach = np.array(t.centroid) - np.array(first_seen)
            approach_dist = float(np.linalg.norm(approach))
            if approach_dist < 1e-6:
                continue
            to_center = cluster_centroid - np.array(first_seen)
            norm = float(np.linalg.norm(to_center))
            if norm < 1e-6:
                continue
            cos_sims.append(float(np.dot(approach, to_center) / (approach_dist * norm)))

        if cos_sims and (sum(cos_sims) / len(cos_sims)) > self.convergence_cos_threshold:
            score = self.confirmed_score
            reasons.append(f"crowd: convergence confirmed (mean cos-sim {sum(cos_sims) / len(cos_sims):.2f})")

        result.score = score
        result.reasons = reasons
        result.fired_track_ids = list(member_ids)
        return result
