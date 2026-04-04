from tool_message_bus import message_bus

if __name__ == "__main__":
    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        message_bus.send("user", "mainAgent", user_input)
