import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
PENDING_TASKS_DIR = REPO_ROOT / "clinic-ai-assistant docs" / "ProjectTasks_Pending"
MANUAL_COVERAGE_FILENAME = "manual_testing_coverage.json"
STATUS_VALUES = {"Not Run", "Pass", "Fail"}
DEFAULT_MANUAL_VERIFICATION = {
    "branch_merge_ready": False,
}


class ManualVerificationDashboardError(Exception):
    pass


class ManualVerificationTaskNotFound(ManualVerificationDashboardError):
    pass


class ManualVerificationCoverageUnavailable(ManualVerificationDashboardError):
    pass


class ManualVerificationCoverageInvalid(ManualVerificationDashboardError):
    pass


def _slugify(value: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return lowered or "task"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _task_markdown_path(entry: Path) -> Path | None:
    if entry.is_dir():
        candidate = entry / f"{entry.name}.md"
        return candidate if candidate.exists() else None
    if entry.is_file() and entry.suffix.lower() == ".md":
        return entry
    return None


def _coverage_path_for_entry(entry: Path) -> Path | None:
    if not entry.is_dir():
        return None
    candidate = entry / MANUAL_COVERAGE_FILENAME
    return candidate if candidate.exists() else None


def _extract_current_active_prompt(markdown_text: str) -> str | None:
    match = re.search(
        r"^## Current Active Prompt\s+[-*]\s+`([^`]+)`",
        markdown_text,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return match.group(1).strip()


def _extract_merge_status(markdown_text: str) -> str | None:
    match = re.search(
        r"^## Merge To Main\s+[-*]\s+`?([A-Za-z ]+)`?",
        markdown_text,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return match.group(1).strip()


def _extract_pending_manual_prompt(markdown_text: str) -> dict | None:
    header_pattern = re.compile(
        r"^## Prompt (\d+) - (Pending|Completed|Blocked)\s*$",
        flags=re.MULTILINE,
    )
    matches = list(header_pattern.finditer(markdown_text))
    for index, match in enumerate(matches):
        prompt_number = int(match.group(1))
        status = match.group(2)
        block_start = match.end()
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        block = markdown_text[block_start:block_end]
        if status != "Pending":
            continue
        if "manual verification" in block.lower() or "merge readiness" in block.lower():
            return {
                "prompt_number": prompt_number,
                "status": status,
            }
    return None


def _task_descriptor(entry: Path) -> dict | None:
    markdown_path = _task_markdown_path(entry)
    if markdown_path is None:
        return None
    markdown_text = _read_text(markdown_path)
    pending_manual_prompt = _extract_pending_manual_prompt(markdown_text)
    if pending_manual_prompt is None:
        return None

    coverage_path = _coverage_path_for_entry(entry)
    task_name = markdown_path.stem
    entry_type = "folder" if entry.is_dir() else "legacy_flat"
    return {
        "id": _slugify(task_name),
        "task_name": task_name,
        "task_file": markdown_path.name,
        "task_relative_path": str(markdown_path.relative_to(REPO_ROOT)),
        "entry_type": entry_type,
        "manual_prompt_number": pending_manual_prompt["prompt_number"],
        "current_active_prompt": _extract_current_active_prompt(markdown_text),
        "merge_to_main": _extract_merge_status(markdown_text),
        "coverage_available": coverage_path is not None,
        "coverage_relative_path": str(coverage_path.relative_to(REPO_ROOT)) if coverage_path else None,
    }


def discover_manual_verification_tasks() -> list[dict]:
    tasks = []
    for entry in sorted(PENDING_TASKS_DIR.iterdir(), key=lambda item: item.name.lower()):
        task = _task_descriptor(entry)
        if task is not None:
            tasks.append(task)
    return tasks


def _get_task_by_id(task_id: str) -> dict:
    for task in discover_manual_verification_tasks():
        if task["id"] == task_id:
            return task
    raise ManualVerificationTaskNotFound(f"Task '{task_id}' was not found")


def _resolve_coverage_path(task: dict) -> Path:
    relative_path = task.get("coverage_relative_path")
    if not relative_path:
        raise ManualVerificationCoverageUnavailable(
            f"Task '{task['task_name']}' does not have {MANUAL_COVERAGE_FILENAME} yet"
        )
    return REPO_ROOT / relative_path


def _validate_row(row: dict, *, category_name: str, test_name: str, row_index: int) -> None:
    if not isinstance(row, dict):
        raise ManualVerificationCoverageInvalid(
            f"Row {row_index} in '{category_name} / {test_name}' must be an object"
        )
    required_string_fields = ["action", "what_is_tested", "status", "comment", "reference_files"]
    for field_name in required_string_fields:
        if not isinstance(row.get(field_name), str):
            raise ManualVerificationCoverageInvalid(
                f"Row {row_index} in '{category_name} / {test_name}' is missing string field '{field_name}'"
            )
    if row["status"] not in STATUS_VALUES:
        raise ManualVerificationCoverageInvalid(
            f"Row {row_index} in '{category_name} / {test_name}' has invalid status '{row['status']}'"
        )
    if not isinstance(row.get("step"), (int, str)):
        raise ManualVerificationCoverageInvalid(
            f"Row {row_index} in '{category_name} / {test_name}' must define 'step' as int or string"
        )


def _validate_coverage_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ManualVerificationCoverageInvalid("Coverage payload must be a JSON object")
    if not isinstance(payload.get("task_name"), str) or not payload["task_name"].strip():
        raise ManualVerificationCoverageInvalid("Coverage payload must contain non-empty 'task_name'")
    if not isinstance(payload.get("task_file"), str) or not payload["task_file"].strip():
        raise ManualVerificationCoverageInvalid("Coverage payload must contain non-empty 'task_file'")
    manual_verification = payload.get("manual_verification")
    if manual_verification is None:
        manual_verification = DEFAULT_MANUAL_VERIFICATION.copy()
        payload["manual_verification"] = manual_verification
    if not isinstance(manual_verification, dict):
        raise ManualVerificationCoverageInvalid("Coverage payload field 'manual_verification' must be an object")
    if not isinstance(manual_verification.get("branch_merge_ready"), bool):
        raise ManualVerificationCoverageInvalid(
            "Coverage payload field 'manual_verification.branch_merge_ready' must be a boolean"
        )
    categories = payload.get("categories")
    if not isinstance(categories, list):
        raise ManualVerificationCoverageInvalid("Coverage payload must contain a 'categories' list")

    not_run = 0
    passed = 0
    failed = 0
    for category in categories:
        if not isinstance(category, dict) or not isinstance(category.get("name"), str):
            raise ManualVerificationCoverageInvalid("Each category must define a string 'name'")
        tests = category.get("tests")
        if not isinstance(tests, list):
            raise ManualVerificationCoverageInvalid(f"Category '{category.get('name', '?')}' must contain a 'tests' list")
        for test in tests:
            if not isinstance(test, dict) or not isinstance(test.get("name"), str):
                raise ManualVerificationCoverageInvalid(
                    f"Category '{category['name']}' contains a test without a string 'name'"
                )
            rows = test.get("rows")
            if not isinstance(rows, list):
                raise ManualVerificationCoverageInvalid(
                    f"Test '{test.get('name', '?')}' in '{category['name']}' must contain a 'rows' list"
                )
            for row_index, row in enumerate(rows, start=1):
                _validate_row(row, category_name=category["name"], test_name=test["name"], row_index=row_index)
                if row["status"] == "Not Run":
                    not_run += 1
                elif row["status"] == "Pass":
                    passed += 1
                elif row["status"] == "Fail":
                    failed += 1

    payload["summary"] = {
        "not_run": not_run,
        "pass": passed,
        "fail": failed,
    }
    return payload


def load_manual_verification_coverage(task_id: str) -> dict:
    task = _get_task_by_id(task_id)
    coverage_path = _resolve_coverage_path(task)
    try:
        payload = json.loads(_read_text(coverage_path))
    except json.JSONDecodeError as exc:
        raise ManualVerificationCoverageInvalid(
            f"Coverage file for '{task['task_name']}' contains invalid JSON"
        ) from exc
    validated_payload = _validate_coverage_payload(payload)
    return {
        "task": task,
        "coverage": validated_payload,
    }


def save_manual_verification_coverage(task_id: str, payload: dict) -> dict:
    task = _get_task_by_id(task_id)
    coverage_path = _resolve_coverage_path(task)
    validated_payload = _validate_coverage_payload(payload)
    coverage_path.write_text(
        json.dumps(validated_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "task": task,
        "coverage": validated_payload,
    }
