import queue
import socket
import threading

import bpy
import dill

from anima.diagnostics import logger
from anima.utils.socket.common import (
    QUEUE_FULL,
    QUEUED,
    TCP_HOST,
    TCP_PORT,
    receive_data,
)


class BlenderSocketServer:
    """Server for receiving and executing commands within the Blender environment.

    Instantiate this class within the Blender subprocess to accept Python code or callable objects from external clients. The commands are then queued for execution in Blender's main thread. Handles socket communication and command queuing to ensure thread-safe execution of commands received from the socket client.

    attributes:
        _execution_queue (queue.Queue): Queue for commands to be executed on the main thread.
        _thread (threading.Thread | None): Background thread for listening to socket connections.
    methods:
        start(): Start the socket server and register the command processing timer.
        stop(): Stop the socket server and cleanup.
    """

    _instance = None
    _server_thread = None
    _is_running = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Single queue for all commands (CALL,CODE) to be executed on main thread
        self._command_queue: queue.Queue[bytes] = queue.Queue(maxsize=10)

    def start(self):
        """Start the socket server and register the command processing timer."""
        if self._is_running:
            logger.info("Socket server already running, skipping start")
            return

        # Register timer to process commands on main thread
        process_cmds = self._execute_queued_commands
        if not bpy.app.timers.is_registered(process_cmds):
            bpy.app.timers.register(process_cmds, first_interval=0.1)

        # Start socket server in background thread
        self._server_thread = threading.Thread(target=self._listen, daemon=True)
        self._server_thread.start()
        self._is_running = True

        logger.info(f"Blender socket server started on {TCP_HOST}:{TCP_PORT}")

    def stop(self):
        """Stop the socket server and cleanup."""
        if self._is_running:
            process_cmds = self._execute_queued_commands
            if bpy.app.timers.is_registered(process_cmds):
                bpy.app.timers.unregister(process_cmds)
            self._server_thread.join(timeout=1.0)  # Wait for thread to finish
            self._is_running = False
            logger.info("Socket server stopped")

    # Private methods -------------------------------------------------------------------------------------- #

    def _listen(self):
        """Main socket server loop."""
        logger.debug("Socket server thread started")
        try:
            with self.__class__._create_server_socket() as sock:
                self._run_server_loop(sock)
        except OSError as e:
            logger.error(f"Port {TCP_PORT} already in use: {e}")
        except Exception as e:
            logger.error(f"Socket server error: {e}")

    @staticmethod
    def _create_server_socket() -> socket.socket:
        """Create and configure the server socket.
        Returns:
            socket.socket: Configured server socket ready to accept connections.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logger.debug(f"Starting socket server on {TCP_HOST}:{TCP_PORT}")
        sock.bind((TCP_HOST, TCP_PORT))
        sock.listen(1)  # Listen for incoming connections
        logger.debug("Socket server is listening for connections")
        return sock

    def _run_server_loop(self, sock: socket.socket):
        """Run the main server loop accepting client connections.
        Args:
            sock: Configured server socket to accept connections
        """
        while True:
            try:
                sock.settimeout(1.0)
                stub, addr = sock.accept()
                if not self._handle_connection(stub, addr):
                    break  # Stop signal received
            except socket.timeout:
                continue
            except socket.error as e:
                logger.error(f"Socket server error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in socket server: {e}")

    def _handle_connection(self, stub: socket.socket, addr: tuple) -> bool:
        """Handle a single client connection.
        Args:
            stub: Client socket connection
            addr: Client address tuple (host, port)
        Returns:
            bool: False if stop signal received, True otherwise
        """
        addr_str = f"{addr[0]}:{addr[1]}"
        stub.settimeout(1.0)

        try:
            with stub:
                data = receive_data(stub)
                return self._handle_request(data, stub, addr_str)
        except Exception as e:
            logger.error(f"Error handling client {addr_str}: {e}")
            return True

    def _handle_request(self, data: bytes, stub: socket.socket, addr_str: str) -> bool:
        """Handle a request received from the client.
        Args:
            data: Raw data received from client
            stub: Client socket stub for sending response
            addr_str: Client address string for logging
        Returns:
            bool: False if stop signal received, True otherwise
        """
        if not data:
            logger.trace("Skipping empty command")
            return True

        logger.info(f"Connection from {addr_str}")

        if data == b"STOP":
            logger.info("Shutting down socket server")
            return False
        elif self._queue_command(data, stub):
            logger.info("Command queued successfully")

        return True

    def _queue_command(self, command: bytes, client_stub: socket.socket) -> bool:
        """Queue a command for main thread execution.
        Args:
            command (bytes): The command to queue, expected as bytes "TYPE: DATA".
            socket_stub (socket.socket): Socket to send response back to the client.
        Returns:
            bool: True if the command was queued successfully, False otherwise.
        """
        try:
            # Queue the command for execution on the main thread and send response to client
            self._command_queue.put(command, timeout=0.2)  # 200ms timeout
            client_stub.sendall(QUEUED.encode())
            return True
        except queue.Full:
            logger.error("Server command queue is full")
            client_stub.sendall(QUEUE_FULL.encode())
            return False
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode command type: {e}")
            return False

    def _execute_queued_commands(self):
        """Process queued commands on main thread. This runs as a Blender timer."""
        try:
            # Process all queued commands
            exec_queue = self._command_queue
            while not exec_queue.empty():
                try:
                    cmd = exec_queue.get_nowait()
                    self.__class__._execute_command(cmd)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error executing queued command: {e}")
        except Exception as e:
            logger.error(f"Error in command processor: {e}")

        # Return 0.1 to keep the timer running every 100ms
        return 0.1

    @staticmethod
    def _execute_command(command: bytes):
        """Execute a command on the main thread.
        Args:
            command (bytes): The command to execute, expected as raw bytes.
        """
        try:
            if not isinstance(command, bytes):
                logger.error(f"Invalid command format: {command}")
                return

            # Unpickle and execute the callable
            func = dill.loads(command)
            logger.debug(f"Executing callable: {func}")
            result = func()
            logger.debug(f"Callable returned: {result}")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
