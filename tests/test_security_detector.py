from src.security.detector import _sanitize_json_value


def test_sanitize_json_value_replaces_nested_nul_characters():
    value = {
        "plain": "unchanged",
        "nul\x00key": "value\x00with\x00nul",
        "nested": ["item\x00", {"tuple": ("a\x00b", 1, None)}],
    }

    assert _sanitize_json_value(value) == {
        "plain": "unchanged",
        "nul\\0key": "value\\0with\\0nul",
        "nested": ["item\\0", {"tuple": ["a\\0b", 1, None]}],
    }
