"""Build a private copy/paste packet from the public grant proposal."""

import argparse
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = BASE_DIR / "proposal" / "form_answers_EN.md"


def extract_field(source: str, number: int) -> str:
    """Extract one numbered field from the canonical English answer file."""
    next_marker = rf"(?=\n## (?:Field {number + 1}:|Submission Gate))"
    match = re.search(
        rf"## Field {number}:[^\n]+\n\n(.*?){next_marker}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Field {number} was not found")
    value = match.group(1).strip()
    value = re.sub(r"\n\n\*\(Word count:.*?\)\*$", "", value, flags=re.DOTALL)
    return value


def normalize_linkedin(value: str) -> str:
    """Normalize and validate the public LinkedIn profile URL."""
    normalized = value.strip()
    if not normalized.startswith(("https://", "http://")):
        normalized = f"https://{normalized}"
    if "linkedin.com/in/" not in normalized.lower():
        raise ValueError("linkedin must be a public linkedin.com/in profile URL")
    return normalized


def build_submission(
    *,
    source: str,
    first_name: str,
    last_name: str,
    email: str,
    linkedin: str,
    role: str,
) -> str:
    """Return a private, form-ordered Markdown submission packet."""
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()) is None:
        raise ValueError("email does not have a valid structure")
    linkedin = normalize_linkedin(linkedin)
    fields = {number: extract_field(source, number) for number in range(1, 7)}
    title = fields[1].strip("*")
    sentence = fields[2].strip()
    other_people = (
        "No additional team member is named at submission. An independent case "
        "author/test custodian and a separate protocol approver will be contracted "
        "or selected and named before protocol freeze."
    )
    return f"""# PRIVATE — OpenAI Cybersecurity Grant submission packet

Do not commit this file to a public repository. Review every field in the official
form before submission.

## Step 1 — Applicant Information

First name: {first_name.strip()}

Last name: {last_name.strip()}

Email: {email.strip()}

Company or University: [leave blank — individual application]

Role / Title: {role.strip()}

LinkedIn: {linkedin}

Other people working on the project:
{other_people}

Additional notes:
This is an individual application for an open defensive laboratory benchmark. No
confidential dataset, personal dataset, production credential, or employer-owned
material is being submitted. The v0.6 test dataset does not yet exist.

## Step 2 — Project Proposal

### Project title

{title}

### One descriptive sentence

{sentence}

### Project proposal — paste as plaintext

{fields[4]}

### Problem statement — 200 words maximum

{fields[3]}

### PDF link

[leave blank — the complete information is in the project proposal]

### Relevant authored papers

[leave blank unless a genuinely published authored paper is added before submission]

### Project timeline

{fields[5]}

### Requested funding / API credits / resources

{fields[6]}

## Final human gate

- Confirm the first-name/last-name split against the applicant's identity document.
- Re-read the current program terms and privacy statements.
- Confirm that no confidential or employer-owned information is present.
- Submission requires the applicant's explicit approval in a separate action.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--linkedin", required=True)
    parser.add_argument(
        "--role",
        default="IT Leader and Independent Researcher",
    )
    args = parser.parse_args()
    print(
        build_submission(
            source=args.source.read_text(encoding="utf-8"),
            first_name=args.first_name,
            last_name=args.last_name,
            email=args.email,
            linkedin=args.linkedin,
            role=args.role,
        )
    )


if __name__ == "__main__":
    main()
