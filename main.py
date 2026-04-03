from agent import mainAgent
from message_bus import message_bus
import threading

if __name__ == "__main__":
    # run main agent at background

    threading.Thread(target=mainAgent.run_loop, daemon=True).start()

    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        message_bus.send("user", "mainAgent", user_input)
