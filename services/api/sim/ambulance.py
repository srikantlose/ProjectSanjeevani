"""Ambulance dispatch simulation (plan.md §9.3).

E5-T4 ships a stub that only logs; E6-T3 replaces this with real nearest-ambulance
selection, routing, and an asyncio movement loop.
"""

from __future__ import annotations

from services.api.models import Incident


def dispatch_incident(incident: Incident) -> None:
    print(
        f"[dispatch stub] would dispatch nearest ambulance to incident {incident.id} "
        f"at ({incident.lat}, {incident.lon})"
    )
