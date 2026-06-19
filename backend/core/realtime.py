"""In-memory realtime event bus for prototype SSE feeds."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import AsyncIterator


class RealtimeEventBus:
    def __init__(self, max_history: int = 100) -> None:
        self._subscribers: set[asyncio.Queue[dict]] = set()
        self._history: deque[dict] = deque(maxlen=max_history)

    def publish(self, event: dict) -> None:
        self._history.append(event)
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[str]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            for event in self._history:
                yield self._format_sse(event)
            while True:
                event = await queue.get()
                yield self._format_sse(event)
        finally:
            self._subscribers.discard(queue)

    def _format_sse(self, event: dict) -> str:
        return f"data: {json.dumps(event, default=str)}\n\n"


realtime_bus = RealtimeEventBus()
