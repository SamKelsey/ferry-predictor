import csv
from dataclasses import asdict
from pathlib import Path

OBSERVED_AT = 'observed_at'

Row = dict[str, str]


def row(item: object) -> Row:
    """A dataclass as a CSV row, with missing values written as empty strings."""
    return {k: '' if v is None else str(v) for k, v in asdict(item).items()}


def read(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def latest(logged: list[Row], key: tuple[str, ...]) -> dict[tuple[str, ...], Row]:
    """The latest logged values for each key, without when they were observed."""
    return {_key(r, key): _values(r) for r in logged}


def changes(logged: list[Row], observed: list[Row], key: tuple[str, ...]) -> list[Row]:
    """Observed rows that differ from the latest logged row with the same key."""
    last = latest(logged, key)
    return [r for r in observed if last.get(_key(r, key)) != _values(r)]


def missing(logged: list[Row], observed: list[Row], key: tuple[str, ...]) -> list[Row]:
    """The latest logged row for each key that was not observed."""
    seen = {_key(r, key) for r in observed}
    return [r for k, r in latest(logged, key).items() if k not in seen]


def record(path: Path, observed: list[Row], key: tuple[str, ...], observed_at: str) -> int:
    """Appends the observed rows that changed since they were last logged, and returns how many there were."""
    new = [{OBSERVED_AT: observed_at, **r} for r in changes(read(path), observed, key)]
    if not new:
        return 0
    write_header = not path.exists()
    with path.open('a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(new[0]))
        if write_header:
            writer.writeheader()
        writer.writerows(new)
    return len(new)


def _key(r: Row, key: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(r[k] for k in key)


def _values(r: Row) -> Row:
    return {k: v for k, v in r.items() if k != OBSERVED_AT}
