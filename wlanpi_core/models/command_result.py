import json
from json import JSONDecodeError


class CommandResult():
    """Returned by run_command"""

    def __init__(self, output: str, error: str, status_code: int):
        self.output = output
        self.error = error
        self.status_code = status_code
        self.success = self.status_code == 0

    def output_from_json(self) -> any:
        try:
            return json.loads(self.output)
        except JSONDecodeError:
            return None