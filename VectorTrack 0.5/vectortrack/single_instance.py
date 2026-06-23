"""Single-instance guard for the desktop app."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtCore import QDir, QLockFile
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

INSTANCE_KEY = "Paragon.VectorTrack.0.5"
RAISE_MESSAGE = b"raise"


class SingleInstanceGuard:
    """Hold a cross-process lock and optional raise-existing handler."""

    def __init__(self) -> None:
        self._lock: Optional[QLockFile] = None
        self._server: Optional[QLocalServer] = None

    def acquire(self) -> bool:
        if os.environ.get("VECTORTRACK_TESTING") == "1":
            return True
        lock_path = QDir.temp().absoluteFilePath(f"{INSTANCE_KEY}.lock")
        lock = QLockFile(lock_path)
        lock.setStaleLockTime(5_000)
        if lock.tryLock(200):
            self._lock = lock
            return True
        return False

    @staticmethod
    def notify_existing() -> None:
        if os.environ.get("VECTORTRACK_TESTING") == "1":
            return
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_KEY)
        if socket.waitForConnected(500):
            socket.write(RAISE_MESSAGE)
            socket.waitForBytesWritten(500)
        socket.close()

    def listen(self, on_raise: Callable[[], None]) -> None:
        if os.environ.get("VECTORTRACK_TESTING") == "1":
            return
        QLocalServer.removeServer(INSTANCE_KEY)
        server = QLocalServer()
        if not server.listen(INSTANCE_KEY):
            return

        def _handle_connection() -> None:
            socket = server.nextPendingConnection()
            if socket is None:
                return
            if socket.waitForReadyRead(300) and bytes(socket.readAll()) == RAISE_MESSAGE:
                on_raise()
            socket.disconnectFromServer()

        server.newConnection.connect(_handle_connection)
        self._server = server
