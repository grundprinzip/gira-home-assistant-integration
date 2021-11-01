import typing


def to_gira_pct(v) -> int:
    return int((v / 256.0) * 100)


def to_hass_byte(v) -> int:
    return int((v / 100.0) * 256)


def to_ga(str_address: str) -> int:
    parts = str_address.split("/")
    return int(parts[0]) * 2048 + int(parts[1]) * 256 + int(parts[2])


def create_cmd(address: int, value: typing.Any, type=1) -> dict:
    return dict([("cmd", type), ("ga", address), ("value", value)])
