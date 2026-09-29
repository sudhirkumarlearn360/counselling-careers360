import pytest

from apps.common.validators import normalise_mobile, valid_email, valid_mobile


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+91 98110 22001", "9811022001"),
        ("098110 22001", "9811022001"),
        ("98110-22001", "9811022001"),
        ("9811022001", "9811022001"),
        ("+919811022001", "9811022001"),
        (" 98110 22001 ", "9811022001"),
    ],
)
def test_cq15_normalise_mobile(raw, expected):
    assert normalise_mobile(raw) == expected
    assert valid_mobile(raw)


@pytest.mark.parametrize("raw", ["12345", "", None, "98110220011", "98110 2200a", "+1 98110 22001"])
def test_cq15_invalid_mobiles(raw):
    assert not valid_mobile(raw)


def test_cq15_valid_email():
    assert valid_email("ankit.p@example.com")
    assert not valid_email("ankit@")
    assert not valid_email("")
