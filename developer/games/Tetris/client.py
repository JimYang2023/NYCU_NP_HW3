import sys
import socket
import pygame
import threading
import queue
from tool.common_protocol import send_json, recv_json
from display import Display


class ReceiverThread(threading.Thread):
    """Background thread to receive messages from server"""
    def __init__(self, sock):
        super().__init__(daemon=True)
        self.sock = sock
        self.msg_queue = queue.Queue()
        self.running = True

    def run(self):
        while self.running:
            try:
                msg = recv_json(self.sock)
                self.msg_queue.put(msg)
            except Exception as e:
                print(f"[PLAYER] Receive error: {e}")
                self.running = False
                break

    def get_message(self):
        """Get next message from queue (non-blocking)"""
        try:
            return self.msg_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self.running = False


def player_run(ip, port):
    """Main player client function"""
    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[PLAYER] Connecting to {ip}:{port}...")
    
    try:
        sock.connect((ip, port))
        print("[PLAYER] Connected!")
    except Exception as e:
        print(f"[PLAYER] Connection failed: {e}")
        return

    # Initialize display
    display = Display()
    clock = pygame.time.Clock()

    # Wait for server messages
    try:
        msg = recv_json(sock)
        if msg["action"] == "waiting":
            print(f"[PLAYER] {msg['msg']}")
            msg = recv_json(sock)

        if msg["action"] == "start":
            role = msg["role"]
            print(f"[PLAYER] Game started! You are Player {role}")
    except Exception as e:
        print(f"[PLAYER] Error during startup: {e}")
        pygame.quit()
        sock.close()
        return

    # Start receiver thread
    receiver = ReceiverThread(sock)
    receiver.start()

    # Main game loop
    running = True
    game_state = {}
    opponent_state = {}
    game_over_result = None

    while running:
        # Process all pending messages
        msg = receiver.get_message()
        while msg:
            if msg["action"] == "frame":
                my_key = f"p{role}"
                opp_key = f"p{3-role}"

                game_state = msg[my_key]
                opponent_state = msg[opp_key]

            elif msg["action"] == "game_over":
                game_over_result = msg["result"]
                print(f"[PLAYER] Game Over: {game_over_result.upper()}")
            
            msg = receiver.get_message()

        # Handle input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                try:
                    send_json(sock, {"action": "disconnect"})
                except:
                    pass

            elif event.type == pygame.KEYDOWN:
                # Only send commands if game is not over
                if not game_over_result:
                    try:
                        if event.key == pygame.K_LEFT:
                            send_json(sock, {"action": "left"})
                        elif event.key == pygame.K_RIGHT:
                            send_json(sock, {"action": "right"})
                        elif event.key == pygame.K_UP:
                            send_json(sock, {"action": "rotate"})
                        elif event.key == pygame.K_DOWN:
                            send_json(sock, {"action": "soft_drop"})
                        elif event.key == pygame.K_SPACE:
                            send_json(sock, {"action": "hard_drop"})
                    except Exception as e:
                        print(f"[PLAYER] Send error: {e}")
                        running = False
                
                # Allow exit with ESC key
                if event.key == pygame.K_ESCAPE:
                    running = False
                    try:
                        send_json(sock, {"action": "disconnect"})
                    except:
                        pass

        # Render game state
        if game_state:
            try:
                display.render(game_state, opponent_state)
                
                # Show game over message on screen
                if game_over_result:
                    screen = display.screen
                    overlay = pygame.Surface((display.screen_width, display.screen_height))
                    overlay.set_alpha(200)
                    overlay.fill((0, 0, 0))
                    screen.blit(overlay, (0, 0))
                    
                    # Result text
                    result_font = pygame.font.Font(None, 72)
                    if game_over_result == "win":
                        result_text = result_font.render("YOU WIN!", True, (0, 255, 0))
                    elif game_over_result == "lose":
                        result_text = result_font.render("YOU LOSE!", True, (255, 0, 0))
                    else:
                        result_text = result_font.render("DRAW", True, (255, 255, 0))
                    
                    text_rect = result_text.get_rect(center=(display.screen_width // 2, 
                                                             display.screen_height // 2 - 50))
                    screen.blit(result_text, text_rect)
                    
                    # Instructions
                    inst_font = pygame.font.Font(None, 32)
                    inst_text = inst_font.render("Press ESC to exit", True, (200, 200, 200))
                    inst_rect = inst_text.get_rect(center=(display.screen_width // 2, 
                                                           display.screen_height // 2 + 50))
                    screen.blit(inst_text, inst_rect)
                    
                pygame.display.flip()   

            except Exception as e:
                print(f"[PLAYER] Render error: {e}")

        clock.tick(60)  # 60 FPS client refresh

    # Cleanup
    print("[PLAYER] Disconnecting...")
    receiver.stop()
    receiver.join(timeout=1)
    pygame.quit()
    sock.close()
    print("[PLAYER] Goodbye!")
