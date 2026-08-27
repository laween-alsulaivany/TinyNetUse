"""Single-instance ownership and local commands for TinyNetUse to prevent multiple instances from running simultaneously."""

import os
import time

from PySide6 import QtCore, QtNetwork
import pywintypes  # catches Windows API exceptions.
import win32api  # gets Windows error codes and closes handles.
import win32con  # provides access-right constants such as SYNCHRONIZE.
import win32event  # creates and opens named mutexes.
import win32ts  # gets the Windows login/session ID.
import winerror  # provides named Windows error codes such as ERROR_ALREADY_EXISTS.

# the unique instance ID for TinyNetUse, used for the mutex and local server names
INSTANCE_ID = "TinyNetUse.A3F1B2C4-9E87-4D56-BF12-7C3A05E91D28"


# Use the Windows login session in the pipe name so RDP sessions stay separate.
def _session_id() -> str:
    return str(win32ts.ProcessIdToSessionId(os.getpid()))


# Create the session-local mutex shared by every TinyNetUse build type.
def _create_mutex(name: str):
    # GetLastError tells us whether this process created or joined the mutex.
    handle = win32event.CreateMutex(None, False, name)
    return handle, win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS


def _close_handle(handle) -> None:
    # handle cleanup is shared by normal shutdown and duplicate-process exits
    if handle:
        win32api.CloseHandle(handle)


def _mutex_exists(name: str) -> bool:
    # opening without ownership lets the quit command watch the original process
    try:
        handle = win32event.OpenMutex(win32con.SYNCHRONIZE, False, name)
    except pywintypes.error:
        return False
    _close_handle(handle)
    return True


class SingleInstance(QtCore.QObject):
    show_requested = QtCore.Signal()
    quit_requested = QtCore.Signal()

    def __init__(self, instance_id: str = INSTANCE_ID):
        super().__init__()
        self.mutex_name = rf"Local\{instance_id}"
        self.server_name = f"{instance_id}.{_session_id()}"
        self._mutex = None
        self._servers = []

    # Return True only for the process that owns the monitor and tray icon.
    def start(self, command: str = "show") -> bool:
        # the mutex decides ownership; the local servers carry commands to the owner
        self._mutex, already_running = _create_mutex(self.mutex_name)
        if already_running:
            _close_handle(self._mutex)
            self._mutex = None
            if self._send_command(command):
                if command == "quit":
                    self._wait_for_exit()
                return False

            # allow a brief startup race before deciding the owner is gone
            # The first process may have died before opening its local server.
            self._mutex, already_running = _create_mutex(self.mutex_name)
            if already_running:
                _close_handle(self._mutex)
                self._mutex = None
                return False

        self._start_server("show", self.show_requested)
        self._start_server("quit", self.quit_requested)
        return True

    def _start_server(self, command: str, signal) -> None:
        # each command gets its own session-local endpoint and Qt signal
        server = QtNetwork.QLocalServer(self)
        server.setSocketOptions(
            QtNetwork.QLocalServer.SocketOption.UserAccessOption
        )
        server.newConnection.connect(
            lambda srv=server, sig=signal: self._accept_connections(srv, sig)
        )
        name = f"{self.server_name}.{command}"

        if server.listen(name):
            self._servers.append(server)
            return

        # remove a stale endpoint before retrying after an unclean shutdown
        # On Unix a crash can leave the socket file behind.
        QtNetwork.QLocalServer.removeServer(name)
        if not server.listen(name):
            error = server.errorString()
            self.close()
            raise RuntimeError(f"Could not start TinyNetUse IPC: {error}")
        self._servers.append(server)

    def _send_command(self, command: str) -> bool:
        # startup can lag behind mutex creation, so retry briefly while it binds
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            socket = QtNetwork.QLocalSocket()
            socket.connectToServer(f"{self.server_name}.{command}")
            if socket.waitForConnected(200):
                socket.disconnectFromServer()
                return True
            socket.abort()
            time.sleep(0.05)
        return False

    def _accept_connections(self, server, signal) -> None:
        # drain every queued request and translate it into the matching signal
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            socket.disconnectFromServer()
            socket.deleteLater()
            signal.emit()

    def _wait_for_exit(self) -> None:
        # quit callers wait until the owner releases the mutex
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _mutex_exists(self.mutex_name):
            time.sleep(0.05)

    # Tests use this directly. Production keeps the mutex until process exit.
    def close(self) -> None:
        # stop IPC first, then release ownership so a new process can start
        for server in self._servers:
            name = server.serverName()
            server.close()
            QtNetwork.QLocalServer.removeServer(name)
        self._servers.clear()
        _close_handle(self._mutex)
        self._mutex = None
