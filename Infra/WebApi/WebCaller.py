import requests


class WebCallerError(Exception):
    pass


class WebCaller:

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def get(self, url: str) -> requests.Response:
        try:
            return requests.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            raise WebCallerError(f"GET {url} failed: {e}") from e
