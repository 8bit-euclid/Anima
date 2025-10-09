import socket

TCP_HOST = "127.0.0.1"  # Localhost for Blender socket communication
TCP_PORT = 65432  # Default port
PACKET_SIZE = 4096  # Size (bytes) of each packet to read from the socket

QUEUED = "QUEUED"
QUEUE_FULL = "QUEUE_FULL"


def receive_data(socket_stub: socket.socket) -> bytes:
    """Receive all data from a socket connection.
    Args:
        socket_stub (socket.socket): The socket stub to receive data from.
    Returns:
        bytes: The received raw data.
    """
    data = []
    while True:
        try:
            packet = socket_stub.recv(PACKET_SIZE)
            if not packet:
                break
            data.append(packet)
            if len(packet) < PACKET_SIZE:
                break
        except socket.timeout:
            break
    return b"".join(data)
