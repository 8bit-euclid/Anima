import dill
import functools
import socket
import time
from typing import Callable
from anima.diagnostics import logger
from anima.utils.socket.common import TCP_HOST, TCP_PORT, QUEUE_FULL, QUEUED, receive_data


class BlenderSocketClient:
    """Client for sending commands to the Blender socket server.

    Instantiate this class in the main thread of the run.py script to send Python code or callable objects for execution in the Blender environment. Handles communication with the socket server running in a separate thread within the Blender subprocess.
    """

    @staticmethod
    def execute(func: Callable, *args, **kwargs) -> bool:
        """Run a callable object in the Blender Python environment.
        Args:
            func (callable): The callable to run
            *args: Positional arguments for the callable
            **kwargs: Keyword arguments for the callable
        """
        if not callable(func):
            logger.error("The provided object is not callable")
            return False
        if args or kwargs:
            func = functools.partial(func, *args, **kwargs)
        logger.debug(f"Requesting execution of callable: {func}")
        return BlenderSocketClient._send_request(dill.dumps(func))

    @staticmethod
    def stop_server() -> bool:
        """Stop the Blender socket server."""
        logger.info("Stopping Blender socket server...")
        return BlenderSocketClient._send_request(b"STOP")

    # Private methods -------------------------------------------------------------------------------------- #

    @staticmethod
    def _wait_for_server(max_tries: int = 50, retry_in: float = 0.1):
        """Wait for the server to become ready, with timeout.
        Args:
            max_tries (int): Maximum number of attempts to check server readiness.
            retry_in (float): Time interval between attempts, in seconds.
        """
        m = max_tries
        for i in range(m):
            if BlenderSocketClient._is_server_ready():
                logger.debug(f"Socket server ready after {i+1} attempts")
                return True
            logger.trace(f"Socket server not ready: attempt {i+1}/{m}")
            time.sleep(retry_in)

        logger.warning(f"Socket server not ready after {m} attempts")
        return False

    @staticmethod
    def _is_server_ready(timeout: float = 0.2) -> bool:
        """Check if the socket server is ready to accept connections.
        Args:
            timeout (float): Timeout for the connection attempt, in seconds.
        Returns:
            bool: True if the server is ready, False otherwise.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((TCP_HOST, TCP_PORT))
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def _send_request(data: bytes) -> bool:
        """Send a request to the Blender socket server.
        Args:
            data (bytes): The data to send, typically serialized Python code or callable.
        Returns:
            bool: True if the command was queued successfully, False otherwise.
        Raises:
            socket.timeout: If the connection to the server times out.
            ConnectionRefusedError: If the server is not running or refuses the connection.
            Exception: If there is an error sending the request or receiving the response.
        """
        BlenderSocketClient._wait_for_server()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stub:
                stub.settimeout(3.0)  # 3 second timeout
                stub.connect((TCP_HOST, TCP_PORT))

                # Construct the full command
                logger.debug(f"Sending server request...")
                stub.sendall(data)
                BlenderSocketClient._handle_response(stub)
                return True
        except socket.timeout:
            logger.error(f"Connection to {TCP_HOST}:{TCP_PORT} timed out")
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused to {TCP_HOST}:{TCP_PORT}")
            return False
        except Exception as e:
            logger.error(f"Failed to send request: {e}")
            return False

    @staticmethod
    def _receive_response(stub: socket.socket) -> str:
        """Receive and decode a response from the server socket.
        Args:
            stub (socket.socket): The socket to receive data from.
        Returns:
            str: The decoded response from the server.
        Raises:
            Exception: If there is an error receiving or decoding the response.
        """
        try:
            data = receive_data(stub)
            res = data.decode()
            logger.debug(f"Received server response: {res}")
            return res
        except Exception as e:
            logger.error(f"Error receiving server response: {e}")
            return ""

    @staticmethod
    def _handle_response(stub: socket.socket) -> bool:
        """Handle response from the Blender socket server after sending a command.
        Args:
            sock (socket.socket): The socket to handle the response from.
        Returns:
            bool: True if the command was queued successfully, False otherwise.
        """
        try:
            res = BlenderSocketClient._receive_response(stub)
            if res == QUEUED:
                logger.debug("Server queued command successfully")
                return True
            elif res == QUEUE_FULL:
                logger.error("Server command queue is full")
                return False
            logger.trace(f"Unknown server response: {res}")
            return False
        except Exception as e:
            logger.error(f"Error receiving server response: {e}")
            return False
