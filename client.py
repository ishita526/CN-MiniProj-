import socket
import threading

# Define server address and port to connect to
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


def receive_messages(client_socket):
    """
    This function runs in a BACKGROUND THREAD.
    It continuously listens for incoming messages from the server
    (which are broadcasts from other clients) and prints them immediately.

    Without this separate thread, we could only receive a message AFTER
    typing and sending one — we'd miss messages sent while we were typing.
    """
    while True:
        try:
            # Block and wait for a message arriving from the server
            data = client_socket.recv(1024)

            if not data:
                # Server closed the connection
                print("\n[-] Disconnected from server.")
                break

            message = data.decode("utf-8")
            # Print the incoming message on a new line so it doesn't
            # interrupt the "You: " prompt visually
            print(f"\n{message}\nYou: ", end="", flush=True)

        except Exception:
            # Socket was closed (e.g., we typed 'exit' in the main thread)
            break


def start_client():
    # Step 1: Create a TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Step 2: Connect to the server
        print(f"[*] Connecting to server at {SERVER_HOST}:{SERVER_PORT}...")
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print("[+] Connected to server.")

        # Step 3: Ask for a username to identify this client on the server
        username = input("Enter your username: ").strip()
        while not username:
            username = input("Username cannot be empty. Enter your username: ").strip()

        # Send the username as the very first message to the server
        # The server reads this first to register who this client is
        client_socket.send(username.encode("utf-8"))

        # Step 4: Start the background listener thread
        # This thread handles ALL incoming messages (broadcasts from other clients)
        # independently, so the main thread can stay focused on sending
        listener_thread = threading.Thread(
            target=receive_messages,
            args=(client_socket,),
            daemon=True   # Dies automatically when the main program exits
        )
        listener_thread.start()

        print("[*] Type a message and press Enter. Type 'exit' to quit.\n")

        # Step 5: Main thread — send loop
        while True:
            # Read user input from keyboard
            message = input("You: ").strip()

            if not message:
                continue

            # Send message to server (server will broadcast it to others)
            client_socket.send(message.encode("utf-8"))

            # If user typed 'exit', stop sending
            if message.lower() == "exit":
                print("[*] Leaving chat...")
                break

    except ConnectionRefusedError:
        print(f"[!] Could not connect to {SERVER_HOST}:{SERVER_PORT}. "
              f"Is server.py running?")
    except KeyboardInterrupt:
        print("\n[*] Interrupted.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        # Step 6: Close socket — also causes the listener thread to exit
        client_socket.close()
        print("[*] Disconnected.")


if __name__ == "__main__":
    start_client()
