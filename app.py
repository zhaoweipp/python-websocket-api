import os

import socketio
from apiflask import APIFlask

from serial_manager import SerialManager
from socket_manager import SocketManager


SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "115200"))
SERIAL_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", "0.05"))
STICKY_IDLE_SECONDS = float(os.getenv("STICKY_IDLE_SECONDS", "0.02"))

socket_manager = SocketManager(ping_interval=25, ping_timeout=20)
sio = socket_manager.sio
http_app = APIFlask(__name__)

serial_manager = SerialManager(
    serial_port=SERIAL_PORT,
    serial_baudrate=SERIAL_BAUDRATE,
    serial_timeout=SERIAL_TIMEOUT,
    sticky_idle_seconds=STICKY_IDLE_SECONDS,
)


@http_app.get("/health")
async def health():
    return {"status": "ok"}


@sio.event
async def connect(sid, environ, auth):
    await socket_manager.emit_connected(sid)


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

    ok = serial_manager.send(bytes(payload))
    return {"ok": ok}


app = socketio.ASGIApp(sio, http_app)


@sio.event
async def startup():
    serial_manager.start(socket_manager.emit_serial_data)


@sio.event
async def shutdown():
    serial_manager.stop()
