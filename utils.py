import os
import subprocess


def compact():
    # This is a placeholder for the actual compaction logic, which could involve summarizing or pruning messages.
    return "Conversation history compacted to reduce token usage."


def read_file(filename: str) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error reading file '{filename}': {str(e)}")


def write_file(filename: str, content: str) -> str:
    try:
        with open(filename, "w") as f:
            f.write(content)
        return f"File '{filename}' written successfully."
    except Exception as e:
        raise Exception(f"Error writing file '{filename}': {str(e)}")


def edit_file(filename: str, old_content: str, new_content: str) -> str:
    if not os.path.isfile(filename):
        raise Exception(f"Error: File '{filename}' does not exist.")
    try:
        with open(filename, "r") as f:
            content = f.read()
        if old_content not in content:
            raise Exception(f"Error: Old content not found in '{filename}'.")
        updated_content = content.replace(old_content, new_content)
        with open(filename, "w") as f:
            f.write(updated_content)
        return f"File '{filename}' edited successfully."
    except Exception as e:
        raise Exception(f"Error editing file '{filename}': {str(e)}")


def sub_prompt(prompt: str) -> str:
    return prompt


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        raise Exception("Error: Dangerous command blocked")
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired as e:
        raise Exception(f"Error: Command timed out: {str(e)}")
