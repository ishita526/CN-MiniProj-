import asyncio
import websockets

# Target TCP Chat Server settings
TCP_SERVER_HOST = "127.0.0.1"
TCP_SERVER_PORT = 5000

# WebSocket Bridge settings (used by browser clients)
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765

# Track active WebSocket clients and their associated usernames
active_users = {}  # { websocket_connection: username }
users_lock = asyncio.Lock()


async def broadcast_online_users():
    """
    Broadcasts the current active user list to all connected browser clients.
    """
    user_list = list(active_users.values())
    sync_message = f"[Server] ONLINE_USERS: {', '.join(user_list)}"
    for ws in list(active_users.keys()):
        try:
            await ws.send(sync_message)
        except Exception:
            pass


async def bridge_handler(websocket):
    """
    Handles a single browser WebSocket connection.
    Bridges communication between Browser WebSocket <--> Python TCP Socket.
    """
    username = None
    tcp_reader = None
    tcp_writer = None

    try:
        # Step 1: Receive the username from the browser as the first message
        raw_username = await websocket.recv()
        username = str(raw_username).strip()
        if not username:
            await websocket.close()
            return

        # Step 2: Open a real TCP socket connection to the existing TCP chat server
        try:
            tcp_reader, tcp_writer = await asyncio.open_connection(
                TCP_SERVER_HOST, TCP_SERVER_PORT
            )
        except ConnectionRefusedError:
            error_message = (
                f"[Server] Connection Error: Could not connect to TCP server at "
                f"{TCP_SERVER_HOST}:{TCP_SERVER_PORT}. Please ensure server.py is running."
            )
            print(f"[!] {error_message}")
            await websocket.send(error_message)
            await websocket.close()
            return

        # Step 3: Send the username as the first TCP payload (matches client.py protocol)
        tcp_writer.write(username.encode("utf-8"))
        await tcp_writer.drain()

        # Register this client in the active users directory
        async with users_lock:
            active_users[websocket] = username
            await broadcast_online_users()

        print(f"[+] Bridge connected: '{username}' <--> TCP Server ({TCP_SERVER_HOST}:{TCP_SERVER_PORT})")

        # Step 4: Two-way streaming
        # A) TCP Server -> Browser WebSocket
        async def tcp_to_ws():
            while True:
                data = await tcp_reader.read(1024)
                if not data:
                    # TCP server closed connection
                    break
                message = data.decode("utf-8")
                await websocket.send(message)

        # B) Browser WebSocket -> TCP Server
        async def ws_to_tcp():
            async for message in websocket:
                tcp_writer.write(message.encode("utf-8"))
                await tcp_writer.drain()

        # Run both tasks concurrently until one of them completes (disconnect)
        done, pending = await asyncio.wait(
            [asyncio.create_task(tcp_to_ws()), asyncio.create_task(ws_to_tcp())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining task
        for task in pending:
            task.cancel()

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[!] Bridge error for client '{username}': {e}")
    finally:
        # Step 5: Clean up TCP socket and active user registry
        if tcp_writer:
            try:
                tcp_writer.close()
                await tcp_writer.wait_closed()
            except Exception:
                pass

        async with users_lock:
            if websocket in active_users:
                del active_users[websocket]
                await broadcast_online_users()

        if username:
            print(f"[-] Bridge disconnected: '{username}'")


async def main():
    print(f"[*] Starting WebSocket Bridge on ws://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"[*] Relaying to TCP Chat Server on {TCP_SERVER_HOST}:{TCP_SERVER_PORT}")
    async with websockets.serve(bridge_handler, BRIDGE_HOST, BRIDGE_PORT):
        print("[*] WebSocket Bridge is running. Waiting for browser clients...\n")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] WebSocket Bridge shutting down.")
