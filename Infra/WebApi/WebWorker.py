from typing import Any

from Infra.WebApi.WebCaller import WebCaller
from Infra.WebApi.WebValidator import WebValidator


class WebWorker:

    def __init__(self, caller: WebCaller | None = None, validator: WebValidator | None = None):
        self.caller = caller or WebCaller()
        self.validator = validator or WebValidator()

    def fetch_json(self, url: str) -> Any:
        response = self.caller.get(url)
        self.validator.validate_response(response)
        return self.validator.parse_json(response.text)
