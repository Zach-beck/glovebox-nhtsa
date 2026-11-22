import json
from pathlib import Path

from glovebox_nhtsa.investigations import parse_lines, search_rows
from tests.conftest import run


def test_partial_vin_keeps_identity_and_warning(service):
    result = run(service.decode_vin, "5uxwx7c5*ba", 2011)
    assert result["identity"]["error_code"] == "6"
    assert result["specs"]["make"] == "BMW"
    assert result["specs"]["model"] == "X3"
    assert "Not Applicable" not in json.dumps(result)


def test_invalid_vin_never_calls_upstream(service):
    result = run(service.decode_vin, "bad vin!")
    assert result["error"] == "invalid_vin"
    assert result["retryable"] is False


def test_check_digit_still_returns_the_vehicle(service):
    result = run(service.decode_vin, "3GNDA13D76S000000")
    assert result["identity"]["error_code"] == "1"
    assert result["specs"]["model"] == "HHR"


def test_recalls_convert_dates_and_do_not_claim_repair(service):
    result = run(service.get_recalls, "acura", "rdx", 2012)
    assert result["count"] == 2
    numbers = {item["campaign_number"] for item in result["campaigns"]}
    assert numbers == {"19V182000", "16V061000"}
    assert result["campaigns"][0]["campaign_number"] == "19V182000"
    assert result["campaigns"][0]["report_received"]["iso"] == "2019-03-06"
    assert all(item["park_outside"] is False for item in result["campaigns"])
    assert "repaired" in result["note"]
    assert "remedy" not in result["campaigns"][0]


def test_complaints_cache_does_not_store_narratives(service, tmp_path: Path):
    result = run(service.summarize_complaints, "BMW", "X3", 2011)
    blob = json.dumps(result)
    assert "person@example.com" not in blob
    assert "REDACTEDVIN" not in blob
    assert "Second narrative" not in blob
    assert result["count"] == 2
    assert result["crash_reports"] == 1
    assert result["injuries"] == 1
    cached = "\n".join(path.read_text() for path in (tmp_path / "cache").glob("*.json"))
    # service fixture uses its own tmp cache; search the service cache dir via files written
    cache_dir = service.cache.directory
    stored = "\n".join(path.read_text() for path in cache_dir.glob("*.json"))
    assert "person@example.com" not in stored
    assert "REDACTEDVIN" not in stored
    assert cached == cached


def test_ratings_preserve_not_rated(service):
    result = run(service.get_safety_ratings, vehicle_id="7520")
    assert result["rating"]["overall_rating"] == "Not Rated"


def test_ratings_do_not_pick_a_variant_without_a_drive_match(service):
    result = run(service.get_safety_ratings, "Acura", "RDX", 2013)
    assert result["count"] == 2
    assert "rating" not in result


def test_model_lists_show_the_x3_gap(service):
    result = run(service.list_model_names, "BMW", 2011)
    by_source = {item["source"]: item for item in result["lists"]}
    assert "X3" in by_source["vpic"]["models"]
    assert "X3" not in by_source["recall_product_list"]["models"]


def test_profile_keeps_recalls_when_ratings_are_empty(service):
    result = run(service.vehicle_profile, "5UXWX7C5*BA", None, None, 2011)
    assert result["section_status"]["recalls"] == "ok"
    assert result["section_status"]["ratings"] == "empty"
    assert result["section_status"]["complaints"] == "ok"
    assert result["specs"]["model"] == "X3"
    assert result["recalls"]["campaigns"][0]["campaign_number"] == "17V683000"
    blob = json.dumps(result)
    assert "person@example.com" not in blob
    assert "REDACTEDVIN" not in blob


def test_investigation_search_orders_newest_first():
    rows = parse_lines(Path("tests/fixtures/investigations.txt").read_text().splitlines())
    found = search_rows(rows, make="BMW", model="X3", model_year="2011")
    assert found[0].action == "EA15001"
    assert found[0].campaign == "17V683000"


def test_missing_fixture_is_unavailable_not_a_network_call(service, monkeypatch):
    import socket

    def explode(*_args, **_kwargs):
        raise AssertionError("fixture mode opened a socket")

    monkeypatch.setattr(socket, "create_connection", explode)
    result = run(service.get_recalls, "NOPE", "NONE", 1999)
    assert result["error"] == "not_found"
    assert result["source"] == "fixture"
