import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from schema import Scheme


@dataclass
class FieldError:
    field: str
    message: str
    input_value: object = None


@dataclass
class ValidationResult:
    path: Optional[Path]
    is_valid: bool
    scheme: Optional[Scheme] = None
    errors: List[FieldError] = field(default_factory=list)


def validate_scheme_dict(data: dict) -> ValidationResult:
    """
    Validate a parsed JSON object against the Scheme schema.

    Returns pass/fail plus one FieldError per failing field (field path +
    message + the offending value) instead of a bare try/except boolean,
    so a batch pipeline can log exactly what was wrong with each file.
    """

    try:
        scheme = Scheme.model_validate(data)
        return ValidationResult(path=None, is_valid=True, scheme=scheme)

    except ValidationError as exc:

        errors = [
            FieldError(
                field=".".join(str(part) for part in err["loc"]) or "<root>",
                message=err["msg"],
                input_value=err.get("input"),
            )
            for err in exc.errors()
        ]

        return ValidationResult(path=None, is_valid=False, errors=errors)


def validate_json_file(path: Path) -> ValidationResult:
    """
    Load a JSON file from disk and validate it against the Scheme schema.

    Distinguishes three failure modes so callers can log the right thing:
      - file unreadable
      - not valid JSON at all
      - valid JSON, but fails schema validation (with field-level detail)
    """

    try:
        raw_text = path.read_text(encoding="utf-8")

    except OSError as exc:
        return ValidationResult(
            path=path,
            is_valid=False,
            errors=[FieldError(field="<file>", message=f"Could not read file: {exc}")],
        )

    try:
        data = json.loads(raw_text)

    except json.JSONDecodeError as exc:
        return ValidationResult(
            path=path,
            is_valid=False,
            errors=[FieldError(field="<json>", message=f"Invalid JSON: {exc}")],
        )

    result = validate_scheme_dict(data)
    result.path = path

    return result


def validate_folder(folder: Path) -> List[ValidationResult]:
    return [validate_json_file(p) for p in sorted(folder.glob("*.json"))]


# ==========================================================
# CLI — audit an existing json_output/ folder
# ==========================================================

if __name__ == "__main__":

    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataset/gov_myscheme/json_output")

    if not folder.exists():
        print(f"Folder not found: {folder.resolve()}")
        sys.exit(1)

    results = validate_folder(folder)

    valid = [r for r in results if r.is_valid]
    invalid = [r for r in results if not r.is_valid]

    print("=" * 80)
    print("JSON SCHEMA VALIDATION")
    print("=" * 80)
    print(f"Folder    : {folder.resolve()}")
    print(f"Total     : {len(results)}")
    print(f"Valid     : {len(valid)}")
    print(f"Invalid   : {len(invalid)}")
    print("=" * 80)

    if invalid:

        print("\nINVALID FILES\n")

        for result in invalid:
            print(f"- {result.path.name}")
            for err in result.errors:
                print(f"    {err.field}: {err.message}")

        sys.exit(1)

    print("\nAll files passed schema validation.")
