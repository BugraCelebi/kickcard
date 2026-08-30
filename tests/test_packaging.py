import importlib

SUBPACKAGES = ["ingest", "bot", "game", "economy", "store", "api"]


def test_all_subpackages_import() -> None:
    for name in SUBPACKAGES:
        importlib.import_module(f"kickcard.{name}")
