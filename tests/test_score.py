from evals.score import _arguments_match, normalize_arguments, score_case, summarize
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service
from tests.conftest import FIXTURES, INVESTIGATIONS, run
from tests.golden_cases import CASES


def test_component_arguments_accept_singular_and_plural():
    assert _arguments_match(
        {"make": "BMW", "model": "X3", "model_year": 2011, "component": "BRAKES"},
        {"make": "BMW", "model": "X3", "model_year": 2011, "component": "brake"},
    )


def test_normalize_make_and_vin_spaces():
    assert normalize_arguments({"make": "bmw", "model": "x3", "model_year": 2011}) == {
        "make": "BMW",
        "model": "X3",
        "model_year": 2011,
    }
    assert normalize_arguments({"vin": "5uxw x7c5*ba"}) == {"vin": "5UXWX7C5*BA"}


def test_perfect_replay_scores_every_case(tmp_path):
    settings = Settings(
        fixtures_dir=FIXTURES,
        investigations_file=INVESTIGATIONS,
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        offline=True,
        request_gap_seconds=0,
    )
    service = build_service(settings)
    rows = []
    for case in CASES:
        if case["tool"] is None:
            answer = " ".join(case["must_include"])
            transcript = {"tool_calls": [], "answer": answer}
        else:
            method = getattr(service, case["tool"])
            result = run(method, **case["arguments"])
            transcript = {
                "tool_calls": [{"name": case["tool"], "arguments": case["arguments"], "result": result}],
                "answer": "Quoted from the tool. " + " ".join(case["must_include"]),
            }
        rows.append(score_case(case, transcript))
    summary = summarize(rows)
    assert summary["failures"] == []
    assert summary["tool_selection"]["passed"] == len(CASES)
