from __future__ import annotations

from routing.policy import DEFAULT_QUEUE, ROUTING_TABLE


def route_event(event: dict) -> str:
    event_type = event.get("type")
    return ROUTING_TABLE.get(event_type, DEFAULT_QUEUE)
