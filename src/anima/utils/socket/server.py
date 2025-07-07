import bpy
import socket
import threading
import dill
import queue
from anima.diagnostics import logger

TCP_HOST = '127.0.0.1'  # Localhost for Blender socket communication
TCP_PORT = 65432        # Default port

PREFIX_DELIMITER = ": "
QUEUED = "QUEUED"
QUEUE_FULL = "QUEUE_FULL"

COMMAND_TYPE = tuple[str, bytes]


class BlenderSocketServer:
    """Server for receiving and executing commands within the Blender environment.

    Instantiate this class within the Blender subprocess to accept Python code or callable objects from external clients. The commands are then queued for execution in Blender's main thread. Handles socket communication and command queuing to ensure thread-safe execution of commands received from the socket client.

    attributes:
        _execution_queue (queue.Queue): Queue for commands to be executed on the main thread.
        _thread (threading.Thread | None): Background thread for listening to socket connections.
    methods:
        start(): Start the socket server and register the command processing timer.
        stop(): Stop the socket server and cleanup.
        process_command(command, conn=None): Process a command received from the socket.
        _queue_command(command, conn=None): Queue a command for main thread execution.
    """

    def __init__(self):
        # Single queue for all commands (CALL,CODE) to be executed on main thread
        self._command_queue: queue.Queue[COMMAND_TYPE] = queue.Queue(
            maxsize=10)
        self._thread: threading.Thread | None = None

    def start(self):
        # Register timer to process commands on main thread
        process_cmds = self._execute_queued_commands
        if not bpy.app.timers.is_registered(process_cmds):
            bpy.app.timers.register(process_cmds, first_interval=0.1)

        # Start socket server in background thread
        logger.debug("Creating socket server thread...")
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

        logger.info(f"Blender socket server started on {TCP_HOST}:{TCP_PORT}")

    def stop(self):
        """Stop the socket server and cleanup."""
        process_cmds = self._execute_queued_commands
        if bpy.app.timers.is_registered(process_cmds):
            bpy.app.timers.unregister(process_cmds)
        self._thread.join(timeout=1.0)  # Wait for thread to finish

    # Private methods -------------------------------------------------------------------------------------- #

    def _listen(self):
        logger.debug("Starting socket server thread...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Set socket options to allow reuse of the address
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                # Bind the socket to the specified host and port
                logger.debug(
                    f"Starting socket server on {TCP_HOST}:{TCP_PORT}")
                sock.bind((TCP_HOST, TCP_PORT))
                sock.listen(1)

                while True:
                    try:
                        sock.settimeout(1.0)
                        client_stub, addr = sock.accept()

                        # Receive data from the client
                        client_stub.settimeout(1.0)
                        with client_stub:
                            raw_data = client_stub.recv(1024)
                            if not raw_data:
                                logger.trace(
                                    "Received empty command, skipping")
                                continue

                            logger.debug(
                                f"Connection from {addr[0]}:{addr[1]}")
                            if raw_data == b"STOP":
                                logger.info("Shutting down socket server")
                                break
                            elif self._queue_command(raw_data, client_stub):
                                logger.info("Command queued successfully")
                    except socket.timeout:
                        continue
                    except socket.error as e:
                        logger.error(f"Socket server error: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error in socket server: {e}")
        except OSError as e:
            logger.error(f"Port {TCP_PORT} already in use: {e}")
        except Exception as e:
            logger.error(f"Socket server error: {e}")

    def _queue_command(self, command: bytes, client_stub: socket.socket) -> bool:
        """Queue a command for main thread execution.
        Args:
            command (bytes): The command to queue, expected as bytes "TYPE: DATA".
            socket_stub (socket.socket): Socket to send response back to the client.
        Returns:
            bool: True if the command was queued successfully, False otherwise.
        """
        try:
            delimiter_bytes = PREFIX_DELIMITER.encode()
            if delimiter_bytes not in command:
                logger.error("Invalid command format, missing delimiter")
                return False

            # Split the command into bytes parts
            cmd_type_bytes, python_code_bytes = command.split(
                delimiter_bytes, 1)

            # Decode only the command type, keep data as bytes
            cmd_type = cmd_type_bytes.decode()
            cmd_tuple = (cmd_type, python_code_bytes)

            # Queue the command for execution on the main thread and send response to client
            self._command_queue.put(cmd_tuple, timeout=0.2)  # 200ms timeout
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
                    self._execute_command(cmd)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error executing queued command: {e}")
        except Exception as e:
            logger.error(f"Error in command processor: {e}")

        # Return 0.1 to keep the timer running every 100ms
        return 0.1

    def _execute_command(self, command: tuple[str, bytes]):
        """Execute a command on the main thread."""
        try:
            if not isinstance(command, tuple):
                logger.error(f"Invalid command format: {command}")
                return

            cmd_type, python_code = command
            if cmd_type == "CODE":
                # Execute the Python code directly
                code = python_code.decode()
                exec(code, globals())
                logger.debug(f"Executed code: {code}")
            elif cmd_type == "CALL":
                # Unpickle and execute the callable
                func = dill.loads(python_code)
                result = func()
                logger.debug(f"Executed callable: {func}")
                logger.debug(f"Callable returned: {result}")
            else:
                logger.error(f"Unknown command type: {cmd_type}")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
