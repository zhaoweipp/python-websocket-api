import socketio


class SocketManager:
    def __init__(self, ping_interval: int = 25, ping_timeout: int = 20):
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
        )

    async def emit_connected(self, sid: str) -> None:
        await self.sio.emit("system:connected", {"sid": sid}, to=sid)

    async def emit_serial_data(self, payload: bytes) -> None:
        await self.sio.emit("serial:data", payload)
