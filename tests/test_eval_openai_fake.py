import json

from evals.local import run_openai_cases


class _Body:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> bool:
        return False


def test_openai_eval_parses_a_fake_response_and_sends_the_key_as_a_header():
    seen = {}

    def opener(request, timeout=60):
        del timeout
        seen["auth"] = request.get_header("Authorization")
        seen["url"] = request.full_url
        return _Body({"choices": [{"message": {"content": "decode_vin"}}]})

    report = run_openai_cases(
        "not-a-real-key",
        [{"id": "decode partial bmw", "tool": "decode_vin"}],
        opener=opener,
        model="fake-model",
    )
    assert seen["auth"] == "Bearer not-a-real-key"
    assert seen["url"].startswith("https://api.openai.com/")
    assert report["tool_name_mentions"] == 1
    assert report["cases"] == 1
    assert report["status"] == "completed"
