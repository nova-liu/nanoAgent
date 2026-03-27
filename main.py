from agent_loop import agent_loop


if __name__ == "__main__":
    history = []

    while True:
        user_input = input("User: ")
        history.append({"role": "user", "content": user_input})

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        agent_loop(history)
        response_content = history[-1]["content"]
        print(f"Agent: {response_content}\n")


