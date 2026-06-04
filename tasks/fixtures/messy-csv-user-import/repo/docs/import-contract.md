# User Import Contract

The import receives CSV text with these headers:

```text
name,email,role
```

Rules:

- Use normal CSV parsing, including quoted fields.
- Trim whitespace around names, emails, and roles.
- Store emails in lowercase.
- A blank role means `member`.
- Skip malformed rows, missing-email rows, and duplicate-email rows.
- Report skipped rows with their one-based line number from the original file.
- Continue importing valid rows after invalid rows.
