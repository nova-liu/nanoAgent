from agent_loop import agent_loop, SYSTEM

if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM}]

    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        agent_loop(messages)
        response_content = messages[-1]["content"]
        print(f"Agent: {response_content}\n")
