import time
import json


class TraceCollector:

    def __init__(self):
        self.steps = []
        self.start_time = time.time()

    def log_step(self, node_name, input_data, output_data, duration):

        self.steps.append({
            "node": node_name,
            "input": input_data,
            "output": output_data,
            "duration_ms": duration
        })

    def get_trace(self):
        return json.dumps(self.steps, indent=2)

    def get_duration(self):
        return time.time() - self.start_time