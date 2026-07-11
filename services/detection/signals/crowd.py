"""Crowd-as-signal detection — the project's primary novel contribution (plan.md §7.4).

Detects sudden bystander clustering on the carriageway: a formation-rate check
(cluster gains >= FORMATION_GROWTH_THRESHOLD new members within FORMATION_WINDOW_S)
gated further by a convergence check (are the new members' walking directions
actually converging on the cluster, as opposed to e.g. a stable queue of people
who happen to be standing/walking near each other). This is what fires when the
crash itself is occluded but bystanders react to it.
"""

from __future__ import annotations

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
        self.convergence_cos_threshold = convergence_cos_threshold
        self.formation_only_score = formation_only_score
        self.confirmed_score = confirmed_score
        self._history: deque = deque()

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

        self._history.append(_ClusterObservation(timestamp_s=ts, member_track_ids=member_ids))
        while self._history and ts - self._history[0].timestamp_s > self.formation_window_s:
            self._history.popleft()

        if not member_ids:
            return result

        baseline_ids = self._history[0].member_track_ids
        new_members = member_ids - baseline_ids
        if len(new_members) < self.formation_growth_threshold:
            return result

        score = self.formation_only_score
        reasons = [f"crowd: cluster grew by {len(new_members)} members within {self.formation_window_s:.0f}s"]

        cluster_centroid = np.mean([t.centroid for t in cluster_members], axis=0)
        cos_sims = []
        for t in cluster_members:
            if t.track_id not in new_members:
                continue
            vel = np.array(t.velocity)
            speed = float(np.linalg.norm(vel))
            if speed < 1e-6:
                continue
            to_center = cluster_centroid - np.array(t.centroid)
            norm = float(np.linalg.norm(to_center))
            if norm < 1e-6:
                continue
            cos_sims.append(float(np.dot(vel, to_center) / (speed * norm)))

        if cos_sims and (sum(cos_sims) / len(cos_sims)) > self.convergence_cos_threshold:
            score = self.confirmed_score
            reasons.append(f"crowd: convergence confirmed (mean cos-sim {sum(cos_sims) / len(cos_sims):.2f})")

        result.score = score
        result.reasons = reasons
        result.fired_track_ids = list(member_ids)
        return result
