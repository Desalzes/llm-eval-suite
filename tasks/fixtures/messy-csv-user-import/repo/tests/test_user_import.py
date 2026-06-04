from imports.users import ImportIssue, import_users


def test_import_keeps_valid_rows_and_reports_bad_rows_with_line_numbers() -> None:
    csv_text = "\n".join(
        [
            "name,email,role",
            '"Riley, Sr.",RILEY@example.com,admin',
            "  Sam Patel , SAM@example.com , ",
            "No Email,,viewer",
            "Duplicate Sam,sam@example.com,owner",
            "Malformed Only Name",
            "Jordan Lee,jordan@example.com,viewer",
        ]
    )

    result = import_users(csv_text)

    assert result.users == [
        {"name": "Riley, Sr.", "email": "riley@example.com", "role": "admin"},
        {"name": "Sam Patel", "email": "sam@example.com", "role": "member"},
        {"name": "Jordan Lee", "email": "jordan@example.com", "role": "viewer"},
    ]
    assert result.issues == [
        ImportIssue(line=4, email=None, reason="missing_email"),
        ImportIssue(line=5, email="sam@example.com", reason="duplicate_email"),
        ImportIssue(line=6, email=None, reason="malformed_row"),
    ]


def test_import_handles_blank_and_whitespace_only_input() -> None:
    result = import_users("name,email,role\n  ,  ,  \n")

    assert result.users == []
    assert result.issues == [
        ImportIssue(line=2, email=None, reason="missing_email"),
    ]
