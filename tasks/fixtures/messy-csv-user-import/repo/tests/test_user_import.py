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


def test_quoted_comma_in_name_is_preserved() -> None:
    result = import_users('name,email,role\n"Lee, Jr.",lee@x.io,eng\n')
    assert result.users == [{"name": "Lee, Jr.", "email": "lee@x.io", "role": "eng"}]
    assert result.issues == []


def test_email_lowercased_and_blank_role_defaults_to_member() -> None:
    result = import_users("name,email,role\n  Mia  ,  MIA@MAIL.IO  ,  \n")
    assert result.users == [{"name": "Mia", "email": "mia@mail.io", "role": "member"}]
    assert result.issues == []


def test_malformed_row_skipped_and_later_valid_rows_still_import() -> None:
    result = import_users(
        "\n".join(["name,email,role", "Ana,ana@x.io,eng", "BrokenOneField", "Ben,ben@x.io,ops"])
    )
    assert [u["email"] for u in result.users] == ["ana@x.io", "ben@x.io"]
    assert result.issues == [ImportIssue(line=3, email=None, reason="malformed_row")]


def test_duplicate_email_keeps_first_and_reports_line() -> None:
    result = import_users(
        "\n".join(["name,email,role", "Ana,ana@x.io,eng", "Ana Two,ANA@x.io,ops"])
    )
    assert [u["email"] for u in result.users] == ["ana@x.io"]
    assert result.issues == [ImportIssue(line=3, email="ana@x.io", reason="duplicate_email")]
