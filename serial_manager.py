import asyncio
import threading
import time
from typing import Optional

import serial


class SerialManager:
    def __init__(
        self,
        serial_port: str,
        serial_baudrate: int,
        serial_timeout: float,
        sticky_idle_seconds: float,
    ):
        self.serial_port = serial_port
        self.serial_baudrate = serial_baudrate
        self.serial_timeout = serial_timeout
        self.sticky_idle_seconds = sticky_idle_seconds

        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._on_data = None

    def start(self, on_data) -> None:
        self._on_data = on_data
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
                port=self.serial_port,
                baudrate=self.serial_baudrate,
                timeout=self.serial_timeout,
            )
        except Exception:
            return None

    def _emit_data(self, payload: bytes) -> None:
        if not self._main_loop or not self._on_data:
            return
        fut = asyncio.run_coroutine_threadsafe(self._on_data(payload), self._main_loop)
        try:
            fut.result(timeout=1)
        except Exception:
            pass

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

            if buffer and (now - last_data_at) >= self.sticky_idle_seconds:
                self._emit_data(bytes(buffer))
                buffer.clear()
