import functools
import pickle
import socket
import time
from anima.diagnostics import logger
from anima.utils.socket.server import TCP_HOST, TCP_PORT, PREFIX_DELIMITER, QUEUE_FULL, QUEUED


class BlenderSocketClient:
    """Client for sending commands to the Blender socket server.

    Instantiate this class in the main thread of the run.py script to send Python code or callable objects for execution in the Blender environment. Handles communication with the socket server running in a separate thread within the Blender subprocess.
    """

    def execute_code(self, code: str) -> bool:
        """Run Python code in the Blender Python environment.
        Args:
            code (str): The Python code to run
        """
        logger.debug(f"Requesting execution of code: {code}")
        return send_request(code.encode(), "CODE")

    def execute_callable(self, func, *args, **kwargs) -> bool:
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
        return send_request(pickle.dumps(func), "CALL")


# Standalone functions ------------------------------------------------------------------------------------- #

def wait_for_server(max_tries: int = 50, retry_in: float = 0.1):
    """Wait for the server to become ready, with timeout.
    Args:
        max_tries (int): Maximum number of attempts to check server readiness.
        retry_in (float): Time interval between attempts, in seconds.
    """
    m = max_tries
    for i in range(m):
        if is_server_ready():
            logger.debug(f"Socket server ready after {i+1} attempts")
            return True
        logger.trace(f"Socket server not ready, attempt {i+1}/{m}")
        time.sleep(retry_in)

    logger.warning(f"Socket server not ready after {m} attempts")
    return False


def is_server_ready(timeout: float = 0.2):
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


def send_request(data: bytes, flag: str) -> bool:
    """Send a request to the Blender socket server.
    Args:
        data (bytes): The data to send, typically serialized Python code or callable.
        flag (str): The request flag - either "CODE" or "CALL".
    """
    assert flag in ["CODE", "CALL"], f"Invalid request flag: {flag}"
    wait_for_server()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stub:
            stub.settimeout(3.0)  # 3 second timeout
            stub.connect((TCP_HOST, TCP_PORT))

            # Construct the full command
            logger.debug(f"Sending command with prefix: {flag}")
            prefix = (flag + PREFIX_DELIMITER).encode()
            stub.sendall(prefix + data)
            handle_response(stub)
            return True
    except socket.timeout:
        logger.error(f"Connection to {TCP_HOST}:{TCP_PORT} timed out")
        return False
    except ConnectionRefusedError:
        logger.error(f"Connection refused to {TCP_HOST}:{TCP_PORT}")
        return False
    except Exception as e:
        logger.error(f"Failed to send command with prefix '{flag}': {e}")
        return False


def receive_response(stub: socket.socket) -> str:
    """Receive and decode a response from the server socket."""
    try:
        res = stub.recv(1024).decode()
        logger.debug(f"Received server response: {res}")
        return res
    except Exception as e:
        logger.error(f"Error receiving server response: {e}")
        return ""


def handle_response(stub: socket.socket) -> bool:
    """Handle response from the Blender socket server after sending a command.
    Args:
        sock (socket.socket): The socket to handle the response from.
    Returns:
        bool: True if the command was queued successfully, False otherwise.
    """
    try:
        res = receive_response(stub)
        if res == QUEUED:
            logger.debug("Server queued command successfully")
            return True
        elif res == QUEUE_FULL:
            logger.error("Server command queue is full")
            return False
        logger.error(f"Unknown server response: {res}")
        return False
    except Exception as e:
        logger.error(f"Error receiving server response: {e}")
        return False
