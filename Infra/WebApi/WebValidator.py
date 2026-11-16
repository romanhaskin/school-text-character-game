import json
from typing import Any

class WebValidationError(ValueError):
    pass


class InvalidJsonError(WebValidationError):
    pass


class HttpStatusError(WebValidationError):

    def __init__(self, status_code: int, url: str = ""):
        super().__init__(f"GET {url} returned http status {status_code}")
        self.status_code = status_code


class EmptyResponseError(WebValidationError):
    pass


class WebValidator:

    @staticmethod
    def validate_response(response: Any) -> None:
        if not 200 <= response.status_code < 300:
            raise HttpStatusError(response.status_code, response.url)
        if not response.text or not response.text.strip():
            raise EmptyResponseError(f"GET {response.url} returned nothing... 'nothing beats a jet 2 holiday!'")

    @staticmethod
    def is_json(data: str) -> bool:
        try:
            json.loads(data)
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def parse_json(data: str) -> Any:
        try:
            return json.loads(data)
        except (TypeError, ValueError) as e:
            raise InvalidJsonError(f"data is not valid json: {e}") from e
