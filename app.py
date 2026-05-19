import asyncio
import os
import threading
import time
from typing import Optional

import serial
import socketio
from apiflask import APIFlask


SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "115200"))
SERIAL_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", "0.05"))
STICKY_IDLE_SECONDS = float(os.getenv("STICKY_IDLE_SECONDS", "0.02"))

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=20,
)
http_app = APIFlask(__name__)


@http_app.get("/health")
async def health():
    return {"status": "ok"}


class SerialBridge:
    def __init__(self, sio_server: socketio.AsyncServer):
        self.sio = sio_server
        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self) -> None:
        self._main_loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._serial and self._serial.is_open:
            self._serial.close()

    def send(self, payload: bytes) -> bool:
        if not payload:
            return False
        if not self._serial or not self._serial.is_open:
            return False
        self._serial.write(payload)
        self._serial.flush()
        return True

    def _open_serial(self) -> Optional[serial.Serial]:
        try:
            return serial.Serial(
                port=SERIAL_PORT,
                baudrate=SERIAL_BAUDRATE,
                timeout=SERIAL_TIMEOUT,
            )
        except Exception:
            return None

    def _read_loop(self) -> None:
        buffer = bytearray()
        last_data_at = 0.0
        while not self._stop.is_set():
            if not self._serial or not self._serial.is_open:
                self._serial = self._open_serial()
                if not self._serial:
                    time.sleep(1)
                    continue

            try:
                waiting = self._serial.in_waiting
                chunk = self._serial.read(waiting or 1)
            except Exception:
                try:
                    self._serial.close()
                except Exception:
                    pass
                time.sleep(1)
                continue

            now = time.time()
            if chunk:
                buffer.extend(chunk)
                last_data_at = now
                continue

            if buffer and (now - last_data_at) >= STICKY_IDLE_SECONDS:
                payload = bytes(buffer)
                buffer.clear()
                if self._main_loop:
                    fut = asyncio.run_coroutine_threadsafe(
                        self.sio.emit("serial:data", payload),
                        self._main_loop,
                    )
                    try:
                        fut.result(timeout=1)
                    except Exception:
                        pass


bridge = SerialBridge(sio)


@sio.event
async def connect(sid, environ, auth):
    await sio.emit("system:connected", {"sid": sid}, to=sid)


@sio.event
async def disconnect(sid):
    return None


@sio.on("serial:write")
async def serial_write(sid, data):
    payload = data
    if isinstance(data, str):
        payload = data.encode("utf-8")
    if isinstance(data, list):
        payload = bytes(data)
    if not isinstance(payload, (bytes, bytearray)):
        return {"ok": False, "error": "payload must be bytes|string|byte-list"}

    ok = bridge.send(bytes(payload))
    return {"ok": ok}


app = socketio.ASGIApp(sio, http_app)


@sio.event
async def startup():
    bridge.start()


@sio.event
async def shutdown():
    bridge.stop()
