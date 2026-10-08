import socket
import threading
from datetime import datetime

# Define server host and port
HOST = "127.0.0.1"  # Localhost
PORT = 5000         # Port to listen on

# Log file configuration
LOG_FILE = "chat_logs.txt"
log_lock = threading.Lock()  # Lock to ensure thread-safe writing to the log file

# --- Shared state ---
# Dictionary mapping each client's socket to their username
# e.g. { <socket_obj>: "Alice", <socket_obj>: "Bob" }
clients = {}

# Lock to prevent two threads from modifying `clients` at the same time
# (Race condition protection — important when multiple threads share data)
clients_lock = threading.Lock()


def log_event(author, message):
    """
    Appends a formatted log entry to chat_logs.txt in a thread-safe manner.
    Format: [YYYY-MM-DD HH:MM:SS] Author: Message
    Automatically creates chat_logs.txt if it does not exist.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {author}: {message}\n"
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)


def broadcast(message, sender_socket):
    """
    Send a message to every connected client EXCEPT the one who sent it.
    This is the core of the multi-client relay architecture.
    """
    # Acquire lock so no other thread can modify `clients` while we iterate
    with clients_lock:
        for client_socket in list(clients):
            if client_socket != sender_socket:
                try:
                    client_socket.send(message.encode("utf-8"))
                except Exception:
                    # If sending fails, this client likely disconnected abruptly
                    remove_client(client_socket)


def remove_client(client_socket):
    """
    Safely remove a client from the shared dictionary and close their socket.
    Called when a client disconnects (expected or unexpected).
    """
    if client_socket in clients:
        username = clients[client_socket]
        del clients[client_socket]
        try:
            client_socket.close()
        except Exception:
            pass
        return username
    return None


def handle_client(client_socket, client_address):
    """
    This function runs in its own thread for every connected client.
    It handles the full lifecycle of one client:
      1. Receive username
      2. Announce join to everyone & log join event
      3. Relay messages to all other clients & log chat messages
      4. Announce leave, log leave event, and clean up on disconnect
    """
    try:
        # Step A: First message the client sends is their chosen username
        username_data = client_socket.recv(1024)
        if not username_data:
            client_socket.close()
            return

        username = username_data.decode("utf-8").strip()

        # Register client in the shared dictionary (protected by lock)
        with clients_lock:
            clients[client_socket] = username

        print(f"[+] {username} joined from {client_address}. "
              f"Total clients: {len(clients)}")

        # Log client join event to file
        log_event("SYSTEM", f"{username} joined the chat")

        # Notify all other clients that someone new joined
        broadcast(f"[Server] {username} has joined the chat!", client_socket)

        # Send a welcome message directly to the joining client
        client_socket.send(
            f"[Server] Welcome, {username}! "
            f"{len(clients) - 1} other client(s) are online.".encode("utf-8")
        )

        # Step B: Relay loop — keep receiving messages from this client
        while True:
            # recv() blocks this thread until the client sends something
            data = client_socket.recv(1024)

            # Empty bytes = client closed the connection
            if not data:
                break

            message = data.decode("utf-8").strip()

            # Check for graceful exit command
            if message.lower() == "exit":
                break

            print(f"[{username}]: {message}")

            # Log normal chat message to file
            log_event(username, message)

            # Broadcast the message to every other connected client
            broadcast(f"{username}: {message}", client_socket)

    except Exception as e:
        print(f"[!] Error with client {client_address}: {e}")

    finally:
        # Step C: Clean up when client leaves (for any reason)
        with clients_lock:
            username = remove_client(client_socket)

        if username:
            print(f"[-] {username} disconnected. "
                  f"Total clients: {len(clients)}")
            # Log client leave event to file
            log_event("SYSTEM", f"{username} left the chat")
            # Notify remaining clients
            broadcast(f"[Server] {username} has left the chat.", client_socket)


def start_server():
    # Step 1: Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Step 2: Bind to address and port
        server_socket.bind((HOST, PORT))
        print(f"[*] Server bound to {HOST}:{PORT}")

        # Step 3: Listen — backlog of 5 connections
        server_socket.listen(5)
        print(f"[*] Server is listening. Logs are saved to '{LOG_FILE}'.")
        print("[*] Waiting for clients...\n")

        # Step 4: Accept loop — run forever, accepting any number of clients
        while True:
            # accept() blocks until a new client connects
            client_socket, client_address = server_socket.accept()

            # Step 5: Spawn a NEW THREAD for this client
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True   # Thread dies automatically if server shuts down
            )
            thread.start()

    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
    finally:
        # Close all client sockets cleanly
        with clients_lock:
            for sock in list(clients):
                sock.close()
        server_socket.close()
        print("[*] Server stopped.")


if __name__ == "__main__":
    start_server()
