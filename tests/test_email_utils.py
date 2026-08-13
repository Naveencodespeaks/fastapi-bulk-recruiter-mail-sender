from app.email_utils import parse_and_validate_recipients


def test_parses_multiple_formats_and_removes_duplicates():
    parsed = parse_and_validate_recipients(
        """
        recruiter1@example.com
        RECRUITER1@example.com, recruiter2@example.com;
        recruiter3@example.com
        """
    )

    assert parsed.valid == [
        "recruiter1@example.com",
        "recruiter2@example.com",
        "recruiter3@example.com",
    ]
    assert parsed.duplicate_count == 1
    assert parsed.invalid == []


def test_reports_invalid_addresses():
    parsed = parse_and_validate_recipients(
        "valid@example.com, bad-address, missing-at.example.com"
    )

    assert parsed.valid == ["valid@example.com"]
    assert parsed.invalid == ["bad-address", "missing-at.example.com"]
