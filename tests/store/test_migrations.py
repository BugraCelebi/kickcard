from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def test_migration_filenames_are_sequential() -> None:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert files, "no migration files found"
    for index, path in enumerate(files, start=1):
        assert path.stem.startswith(f"{index:04d}_")


def test_migrations_are_not_empty() -> None:
    for path in MIGRATIONS_DIR.glob("*.sql"):
        assert path.read_text().strip()
