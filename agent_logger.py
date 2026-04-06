import time
import uuid
import json
from contextlib import contextmanager


def now():
    return time.time()


class AgentLogger:
    def __init__(self, name="agent-run"):
        self.run = {
            "run_id": str(uuid.uuid4()),
            "name": name,
            "steps": [],
            "start_time": now(),
            "end_time": None,
        }

    def finish(self):
        self.run["end_time"] = now()
        return self.run

    def save(self, path="agent_log.json"):
        with open(path, "w") as f:
            json.dump(self.run, f, indent=2, ensure_ascii=False)


class StepCtx:
    def __init__(self, logger, step_type, name):
        self.logger = logger
        self.step = {
            "step_id": str(uuid.uuid4()),
            "type": step_type,
            "name": name,
            "input": {},
            "output": {},
            "error": None,
            "start_time": now(),
            "end_time": None,
        }

    def set_input(self, data):
        self.step["input"] = data

    def set_output(self, data):
        self.step["output"] = data

    def set_error(self, err):
        self.step["error"] = str(err)

    def end(self):
        self.step["end_time"] = now()
        self.logger.run["steps"].append(self.step)


@contextmanager
def step(logger: AgentLogger, step_type: str, name: str):
    ctx = StepCtx(logger, step_type, name)
    try:
        yield ctx
    except Exception as e:
        ctx.set_error(e)
        raise
    finally:
        ctx.end()
