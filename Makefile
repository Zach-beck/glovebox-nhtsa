.PHONY: eval-fixture eval-live

eval-fixture:
	uv run pytest

eval-live:
	GLOVEBOX_FIXTURES= uv run python scripts/score_live_tools.py