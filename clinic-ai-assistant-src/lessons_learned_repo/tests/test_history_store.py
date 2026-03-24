# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import pytest

from lessons_learned_repo import history_store


@pytest.fixture()
def isolated_history_db(tmp_path, monkeypatch):
    db_path = tmp_path / "project_history.db"
    monkeypatch.setattr(history_store, "DB_PATH", db_path)
    history_store.init_history_db()
    return history_store


def test_init_history_db_seeds_required_categories(isolated_history_db):
    categories = isolated_history_db.list_requirement_categories()
    category_codes = {item["code"] for item in categories}

    assert {
        "security",
        "gui",
        "business_logic",
        "infrastructure",
        "documentation",
        "lessons_learned_repo",
        "integration",
        "performance",
    }.issubset(category_codes)


def test_create_requirement_requires_existing_category(isolated_history_db):
    with pytest.raises(ValueError, match="Unknown requirement category"):
        isolated_history_db.create_project_requirement(
            req_code="REQ-MISSING-CATEGORY-001",
            title="Invalid category reference",
            category_code="unknown_category",
            description="This should fail cleanly.",
        )


def test_create_and_query_requirements_by_category(isolated_history_db):
    isolated_history_db.create_project_requirement(
        req_code="REQ-PROJ-HISTORY-001",
        title="Project requirements and execution history tracking",
        category_code="lessons_learned_repo",
        description="Create a lightweight SQLite-based project history layer.",
        status="active",
    )
    isolated_history_db.create_project_requirement(
        req_code="REQ-GUI-001",
        title="GUI variants",
        category_code="gui",
        description="Create five GUI variants for the main page.",
        status="proposed",
    )

    llr_requirements = isolated_history_db.list_requirements_by_category("lessons_learned_repo")
    gui_requirements = isolated_history_db.list_requirements_by_category("gui")

    assert [item["req_code"] for item in llr_requirements] == ["REQ-PROJ-HISTORY-001"]
    assert [item["req_code"] for item in gui_requirements] == ["REQ-GUI-001"]


def test_create_execution_requires_existing_requirement(isolated_history_db):
    with pytest.raises(ValueError, match="Unknown project requirement"):
        isolated_history_db.create_requirement_execution(
            req_code="REQ-DOES-NOT-EXIST",
            prompt_text="Implement feature X",
            execution_summary="Attempted execution",
            execution_impact="No requirement record existed.",
        )


def test_multiple_execution_rows_are_preserved_in_order(isolated_history_db):
    isolated_history_db.create_project_requirement(
        req_code="REQ-PROJ-HISTORY-002",
        title="Execution ordering",
        category_code="documentation",
        description="Track multiple execution rows for one requirement.",
        status="active",
    )

    first = isolated_history_db.create_requirement_execution(
        req_code="REQ-PROJ-HISTORY-002",
        prompt_text="Create first artifact",
        execution_summary="Created the first artifact.",
        execution_impact="Initial project artifact now exists.",
    )
    second = isolated_history_db.create_requirement_execution(
        req_code="REQ-PROJ-HISTORY-002",
        prompt_text="Refine artifact",
        execution_summary="Refined the project artifact.",
        execution_impact="Artifact became more operational.",
    )

    executions = isolated_history_db.list_requirement_execution("REQ-PROJ-HISTORY-002")

    assert [item["id"] for item in executions] == [first["id"], second["id"]]
    assert executions[0]["execution_summary"] == "Created the first artifact."
    assert executions[1]["execution_impact"] == "Artifact became more operational."
    assert all(item["created_at"] for item in executions)
    assert executions[0]["git_commit_hash"] is None


def test_create_lesson_links_multiple_execution_rows(isolated_history_db):
    isolated_history_db.create_project_requirement(
        req_code="REQ-LESSON-001",
        title="Lesson creation",
        category_code="lessons_learned_repo",
        description="Create a lesson from execution evidence.",
        status="active",
    )
    first = isolated_history_db.create_requirement_execution(
        req_code="REQ-LESSON-001",
        prompt_text="Execution A",
        execution_summary="Created the first execution.",
        execution_impact="Initial implementation evidence exists.",
    )
    second = isolated_history_db.create_requirement_execution(
        req_code="REQ-LESSON-001",
        prompt_text="Execution B",
        execution_summary="Created the second execution.",
        execution_impact="Refinement evidence exists.",
    )

    lesson = isolated_history_db.create_lesson_learned(
        lesson_code="LESSON-REQ-001",
        title="Keep lessons curated",
        statement="Lessons should be derived from meaningful execution evidence rather than every log row.",
        why_it_matters="A curated layer preserves signal over noise.",
        source_execution_ids=[first["id"], second["id"]],
        status="validated",
    )
    lessons = isolated_history_db.list_lessons_with_labels(lesson_code="LESSON-REQ-001")

    assert lesson["lesson_code"] == "LESSON-REQ-001"
    assert lessons[0]["requirement_code"] == "REQ-LESSON-001"
    assert lessons[0]["category_code"] == "lessons_learned_repo"
    assert lessons[0]["source_execution_ids"] == f"{first['id']}, {second['id']}"


def test_execution_history_with_labels_includes_git_commit_hash(isolated_history_db):
    isolated_history_db.create_project_requirement(
        req_code="REQ-HASH-001",
        title="Git hash tracking",
        category_code="lessons_learned_repo",
        description="Store repo commit hash alongside execution records.",
        status="active",
    )
    isolated_history_db.create_requirement_execution(
        req_code="REQ-HASH-001",
        prompt_text="Apply booking flow fix",
        execution_summary="Recorded execution with commit hash.",
        execution_impact="Repo mapping is now explicit in execution history.",
        git_commit_hash="abc123hash",
    )

    history = isolated_history_db.list_execution_history_with_labels(req_code="REQ-HASH-001")

    assert history[0]["git_commit_hash"] == "abc123hash"
