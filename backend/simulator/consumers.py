import asyncio
import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .simulation_service import service


class SimulationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self._task = asyncio.create_task(self._push_loop())

    async def disconnect(self, close_code):
        task = getattr(self, "_task", None)
        if task:
            task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            msg = json.loads(text_data)
        except Exception:
            return

        if msg.get("type") == "start":
            duration = msg.get("duration", 30)
            service.start(duration_seconds=duration)
        elif msg.get("type") == "stop":
            service.stop()

    async def _push_loop(self):
        while True:
            snap = service.snapshot()
            await self.send(text_data=json.dumps({"type": "snapshot", "data": snap}, ensure_ascii=False))
            await asyncio.sleep(0.5)

