# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib
import json

from fastapi.testclient import TestClient


def _write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_task_workspace(tmp_path):
    repo_root = tmp_path / "repo"
    pending_dir = repo_root / "clinic-ai-assistant docs" / "ProjectTasks_Pending"

    folder_task_dir = pending_dir / "Folder Manual Task"
    _write_text(
        folder_task_dir / "Folder Manual Task.md",
        """# Folder Manual Task

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 4`

## Prompt 4 - Manual Testing - Pending

### Goal

Manual Verification / Merge Readiness
""",
    )
    _write_json(
        folder_task_dir / "manual_testing_coverage.json",
        {
            "task_name": "Folder Manual Task",
            "task_file": "Folder Manual Task.md",
            "status": "pending_manual_verification",
            "manual_verification": {
                "branch_merge_ready": False,
                "general_comment": "",
            },
            "categories": [
                {
                    "name": "Category 1 - Example",
                    "tests": [
                        {
                            "name": "Test 1.1 - Example",
                            "rows": [
                                {
                                    "step": 1,
                                    "action": "Open the dashboard",
                                    "what_is_tested": "Task rows are visible",
                                    "status": "Not Run",
                                    "comment": "",
                                    "reference_files": "",
                                },
                                {
                                    "step": 2,
                                    "action": "Change a status",
                                    "what_is_tested": "Summary is recomputed on save",
                                    "status": "Not Run",
                                    "comment": "",
                                    "reference_files": "proof-a.png, proof-b.pdf",
                                },
                            ],
                        }
                    ],
                }
            ],
            "summary": {
                "not_run": 2,
                "pass": 0,
                "fail": 0,
            },
        },
    )
    _write_text(
        folder_task_dir / "Folder Manual Task FIX 01.md",
        """# Folder Manual Task FIX 01

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 5`

## Prompt 5 - Merge To Main - Pending

### Goal

Manual Verification / Merge Readiness
""",
    )
    _write_json(
        folder_task_dir / "manual_testing_coverage_FIX01.json",
        {
            "task_name": "Folder Manual Task FIX 01",
            "task_file": "Folder Manual Task FIX 01.md",
            "status": "pending_manual_verification",
            "manual_verification": {
                "branch_merge_ready": False,
                "general_comment": "",
            },
            "categories": [
                {
                    "name": "Category 1 - Fix",
                    "tests": [
                        {
                            "name": "Test 1.1 - Retest",
                            "rows": [
                                {
                                    "step": 1,
                                    "action": "Retest the fix row",
                                    "what_is_tested": "Fix follow-up coverage loads separately",
                                    "status": "Not Run",
                                    "comment": "",
                                    "reference_files": "",
                                }
                            ],
                        }
                    ],
                }
            ],
            "summary": {
                "not_run": 1,
                "pass": 0,
                "fail": 0,
            },
        },
    )
    archive_task_dir = pending_dir / "Z Archive Ready Task"
    _write_text(
        archive_task_dir / "Z Archive Ready Task.md",
        """# Z Archive Ready Task

## Merge To Main

- `Completed`

## Current Active Prompt

- `Completed`

## Prompt 1 - Preparation - Completed

### Goal

Implementation setup

## Prompt 2 - Manual Testing - Completed

### Goal

Manual verification is already completed.
""",
    )
    _write_json(
        archive_task_dir / "manual_testing_coverage.json",
        {
            "task_name": "Z Archive Ready Task",
            "task_file": "Z Archive Ready Task.md",
            "status": "manual_verification_completed",
            "manual_verification": {
                "branch_merge_ready": True,
                "general_comment": "Merged and ready to archive",
            },
            "categories": [
                {
                    "name": "Category 1 - Archive",
                    "tests": [
                        {
                            "name": "Test 1.1 - Archive button eligibility",
                            "rows": [
                                {
                                    "step": 1,
                                    "action": "Load archived-ready coverage",
                                    "what_is_tested": "Merged tasks still appear until archived",
                                    "status": "Pass",
                                    "comment": "",
                                    "reference_files": "",
                                }
                            ],
                        }
                    ],
                }
            ],
            "summary": {
                "not_run": 0,
                "pass": 1,
                "fail": 0,
            },
        },
    )

    _write_text(
        pending_dir / "Legacy Manual Task.md",
        """# Legacy Manual Task

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 9`

## Prompt 9 - Pending

### Goal

Manual verification / merge readiness
""",
    )

    _write_text(
        pending_dir / "Non Manual Task.md",
        """# Non Manual Task

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 2`

## Prompt 2 - Pending

### Goal

Implementation only
""",
    )
    return repo_root, pending_dir


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, manual_verification_dashboard, session_trace_logger

    repo_root, pending_dir = _build_task_workspace(tmp_path)

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "manual-dashboard.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)
    monkeypatch.setattr(manual_verification_dashboard, "REPO_ROOT", repo_root)
    monkeypatch.setattr(manual_verification_dashboard, "PENDING_TASKS_DIR", pending_dir)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app), repo_root, pending_dir


def test_dashboard_task_discovery_handles_folder_and_legacy_entries(monkeypatch, tmp_path):
    client, _, _ = _build_client(monkeypatch, tmp_path)

    response = client.get("/manual-verification/tasks")

    assert response.status_code == 200
    payload = response.json()
    task_names = [task["task_name"] for task in payload["tasks"]]

    assert task_names == ["Folder Manual Task", "Folder Manual Task FIX 01", "Z Archive Ready Task"]
    folder_task = payload["tasks"][0]
    fix_task = payload["tasks"][1]
    archive_task = payload["tasks"][2]
    assert folder_task["entry_type"] == "folder"
    assert folder_task["coverage_available"] is True
    assert folder_task["manual_prompt_number"] == 4
    assert folder_task["current_active_prompt"] == "Prompt 4"
    assert folder_task["workflow_state"] == "Ready for Review"
    assert folder_task["prompt_statuses"] == [
        {
            "prompt_number": 4,
            "prompt_suffix": "Manual Testing",
            "status": "Pending",
            "label": "Prompt 4 - Manual Testing - Pending",
        }
    ]
    assert folder_task["entry_kind"] == "primary"
    assert fix_task["entry_type"] == "folder"
    assert fix_task["coverage_available"] is True
    assert fix_task["entry_kind"] == "fix_01"
    assert fix_task["manual_prompt_number"] == 5
    assert fix_task["workflow_state"] == "Ready for Review"
    assert fix_task["task_folder"] == "Folder Manual Task"
    assert archive_task["archive_ready"] is True
    assert archive_task["workflow_state"] == "Ready to Archive"
    assert archive_task["merge_to_main"] == "Completed"
    assert archive_task["manual_prompt_number"] == 2


def test_dashboard_archives_merged_task_folder(monkeypatch, tmp_path):
    client, repo_root, pending_dir = _build_client(monkeypatch, tmp_path)

    response = client.post("/manual-verification/tasks/z-archive-ready-task/archive")

    assert response.status_code == 200
    payload = response.json()
    assert payload["archived_task_name"] == "Z Archive Ready Task"
    assert payload["destination_relative_path"] == (
        "clinic-ai-assistant docs\\ProjectTasks_Done\\Z Archive Ready Task"
    )
    assert not (pending_dir / "Z Archive Ready Task").exists()
    assert (repo_root / "clinic-ai-assistant docs" / "ProjectTasks_Done" / "Z Archive Ready Task").exists()


def test_dashboard_loads_folder_task_coverage(monkeypatch, tmp_path):
    client, _, _ = _build_client(monkeypatch, tmp_path)

    response = client.get("/manual-verification/tasks/folder-manual-task")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"]["task_name"] == "Folder Manual Task"
    assert payload["coverage"]["summary"] == {"not_run": 2, "pass": 0, "fail": 0}
    assert payload["coverage"]["manual_verification"] == {"branch_merge_ready": False, "general_comment": ""}
    rows = payload["coverage"]["categories"][0]["tests"][0]["rows"]
    assert [row["row_id"] for row in rows] == [1, 2]
    assert rows[1]["reference_files"] == "proof-a.png, proof-b.pdf"


def test_dashboard_save_recomputes_summary_and_persists(monkeypatch, tmp_path):
    client, _, pending_dir = _build_client(monkeypatch, tmp_path)

    update_payload = {
        "task_name": "Folder Manual Task",
        "task_file": "Folder Manual Task.md",
        "status": "pending_manual_verification",
        "manual_verification": {
            "branch_merge_ready": True,
            "general_comment": "Overall follow-up note",
        },
        "categories": [
            {
                "name": "Category 1 - Example",
                "tests": [
                    {
                        "name": "Test 1.1 - Example",
                        "rows": [
                            {
                                "step": 1,
                                "action": "Open the dashboard",
                                "what_is_tested": "Task rows are visible",
                                "status": "Pass",
                                "comment": "Looks correct",
                                "reference_files": "",
                            },
                            {
                                "step": 2,
                                "action": "Change a status",
                                "what_is_tested": "Summary is recomputed on save",
                                "status": "Fail",
                                "comment": "Summary badge mismatch",
                                "reference_files": "proof-a.png, proof-b.pdf",
                            },
                        ],
                    }
                ],
            }
        ],
        "summary": {"not_run": 99, "pass": 99, "fail": 99},
    }

    response = client.put(
        "/manual-verification/tasks/folder-manual-task",
        json={"payload": update_payload},
    )

    assert response.status_code == 200
    saved = response.json()["coverage"]
    assert saved["summary"] == {"not_run": 0, "pass": 1, "fail": 1}
    assert saved["manual_verification"] == {"branch_merge_ready": True, "general_comment": "Overall follow-up note"}

    coverage_path = pending_dir / "Folder Manual Task" / "manual_testing_coverage.json"
    persisted = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert persisted["summary"] == {"not_run": 0, "pass": 1, "fail": 1}
    assert persisted["manual_verification"] == {"branch_merge_ready": True, "general_comment": "Overall follow-up note"}
    assert [row["row_id"] for row in persisted["categories"][0]["tests"][0]["rows"]] == [1, 2]
    assert persisted["categories"][0]["tests"][0]["rows"][1]["comment"] == "Summary badge mismatch"


def test_dashboard_rejects_invalid_status_updates(monkeypatch, tmp_path):
    client, _, _ = _build_client(monkeypatch, tmp_path)

    invalid_payload = {
        "task_name": "Folder Manual Task",
        "task_file": "Folder Manual Task.md",
        "status": "pending_manual_verification",
        "categories": [
            {
                "name": "Category 1 - Example",
                "tests": [
                    {
                        "name": "Test 1.1 - Example",
                        "rows": [
                            {
                                "step": 1,
                                "action": "Open the dashboard",
                                "what_is_tested": "Task rows are visible",
                                "status": "Skipped",
                                "comment": "",
                                "reference_files": "",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    response = client.put(
        "/manual-verification/tasks/folder-manual-task",
        json={"payload": invalid_payload},
    )

    assert response.status_code == 400
    assert "invalid status" in response.json()["detail"]


def test_dashboard_html_exposes_task_switcher_and_save_controls(monkeypatch, tmp_path):
    client, _, _ = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/ManualTesting.html")

    assert response.status_code == 200
    assert "Manual Testing Dashboard" in response.text
    assert 'id="taskSelector"' in response.text
    assert 'id="promptStatusSelector"' in response.text
    assert 'id="archiveButton"' in response.text
    assert 'id="saveButton"' in response.text
    assert 'id="branchMergeReadyInput"' in response.text
    assert 'id="generalCommentInput"' in response.text
    assert 'id="statusFilter"' in response.text
    assert 'const TASKS_URL = "/manual-verification/tasks";' in response.text
    assert 'async function handleTaskSelection(taskId)' in response.text
    assert 'id="taskState"' in response.text
    assert 'class="table-scroll"' in response.text


def test_dashboard_html_applies_fix01_layout_and_filter_contract(monkeypatch, tmp_path):
    client, _, _ = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/ManualTesting.html")

    assert response.status_code == 200
    assert "Read-Only Review" not in response.text
    assert "Track pending manual verification work" not in response.text
    assert 'width: calc(100vw - 24px);' in response.text
    assert 'height: calc(100vh - 24px);' in response.text
    assert 'overflow: hidden;' in response.text
    assert '.general-comment-input {' in response.text
    assert '.secondary-button {' in response.text
    assert 'Archive unlocks after Merge To Main is completed' in response.text
    assert '.col-comment {' in response.text
    assert '.col-reference {' in response.text
    assert '<th class="col-row-id">ID</th>' in response.text
    assert 'data-row-id="${escapeHtml(row?.row_id ?? "")}"' in response.text
    assert 'status-select--pass' in response.text
    assert 'status-select--fail' in response.text
    assert 'status-select--not-run' in response.text
    assert 'archiveButton.addEventListener("click", archiveTask);' in response.text
    assert 'No rows match the selected status filter' in response.text
    assert 'statusFilter.addEventListener("change"' in response.text
