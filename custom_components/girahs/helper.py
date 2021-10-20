def to_gira_pct(v) -> int:
    return int((v / 256.0) * 100)


def to_hass_byte(v) -> int:
    return int((v / 100.0) * 256)
