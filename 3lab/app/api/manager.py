import json
from typing import List
from fastapi.websockets import WebSocket


class ConnectionManager:
    def __init__(self):
        # Храним список активных веб-сокет соединений
        self._active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Принимает входящее соединение и добавляет его в список активных.
        """
        await websocket.accept()
        self._active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Удаляет соединение из списка активных.
        """
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """
        Отправляет сообщение всем активным клиентам.
        """
        serialized_message = json.dumps(message)
        for connection in self._active_connections:
            await connection.send_text(serialized_message)