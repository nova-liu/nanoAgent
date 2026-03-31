from agent import mainAgent

if __name__ == "__main__":
    while True:
        user_input = input("User: ")
        mainAgent.append_user_message(user_input)

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        mainAgent.run_loop()

        print(f"Agent: {mainAgent.final_response()}\n")
