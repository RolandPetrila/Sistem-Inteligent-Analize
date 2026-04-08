"""
WebSocket Connection Manager — modul separat pentru a evita circular imports.
Importat din main.py, routers/jobs.py, routers/batch.py, services/job_service.py
"""
import json

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, ws: WebSocket, already_accepted: bool = False):
        if not already_accepted:
            await ws.accept()
        if job_id not in self.active:
            self.active[job_id] = []
        self.active[job_id].append(ws)
        logger.debug(f"WS connected for job {job_id}")

    def disconnect(self, job_id: str, ws: WebSocket):
        if job_id in self.active:
            try:
                self.active[job_id].remove(ws)
            except ValueError:
                pass
            if not self.active[job_id]:
                del self.active[job_id]

    async def broadcast(self, job_id: str, message: dict):
        if job_id in self.active:
            data = json.dumps(message, ensure_ascii=False)
            dead = []
            for ws in self.active[job_id]:
                try:
                    await ws.send_text(data)
                except Exception as e:
                    logger.debug(f"[ws_broadcast] Non-critical: {e}")
                    dead.append(ws)
            for ws in dead:
                try:
                    self.active[job_id].remove(ws)
                except ValueError:
                    pass


ws_manager = ConnectionManager()
