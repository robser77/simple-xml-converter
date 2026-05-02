import pytest
from convert import _sanitize_tag


@pytest.mark.parametrize("name, expected", [
    ("validName_123",  "validName_123"),   # already valid — unchanged
    ("field name",     "field_name"),       # space replaced
    ("field@name!",    "field_name_"),      # special chars replaced
    ("field.name",     "field.name"),       # dot kept
    ("field-name",     "field-name"),       # hyphen kept
    ("1field",         "_1field"),          # leading digit prefixed
    ("123",            "_123"),             # all digits
    ("",               "_"),               # empty string gets placeholder
])
def test_sanitize_tag(name, expected):
    assert _sanitize_tag(name) == expected
