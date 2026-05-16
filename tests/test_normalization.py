from app.services.normalization import normalize_name, normalize_phone, normalize_website


def test_normalize_name_removes_common_suffixes() -> None:
    assert normalize_name("Örnek CNC San. Tic. Ltd. Şti.") == "ornek cnc"


def test_normalize_phone_turkey() -> None:
    assert normalize_phone("0 (232) 123 45 67") == "+902321234567"


def test_normalize_website() -> None:
    assert normalize_website("https://www.example.com/") == "example.com"

