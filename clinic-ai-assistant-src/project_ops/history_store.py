import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "project_history.db"
REPO_ROOT = BASE_DIR.parent
ALLOWED_REQUIREMENT_STATUSES = {"proposed", "active", "completed", "dropped"}
INITIAL_CATEGORY_SEEDS = (
    ("security", "Security", "Security-related project requirements."),
    ("gui", "GUI", "User interface and presentation requirements."),
    ("business_logic", "Business Logic", "Core business rules and backend behavior."),
    ("infrastructure", "Infrastructure", "Platform, environment, and operational infrastructure."),
    ("documentation", "Documentation", "Documentation and sync artifact requirements."),
    ("data", "Data", "Data modeling and persistence requirements."),
    ("integration", "Integration", "Integration requirements across systems or workflows."),
    ("performance", "Performance", "Performance and efficiency requirements."),
)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required.")
    return value.strip()


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _category_row_by_code(connection: sqlite3.Connection, category_code: str):
    normalized_code = _normalize_required_text(category_code, "category_code")
    return connection.execute(
        """
        SELECT id, code, name, description, created_at
        FROM requirement_categories
        WHERE code = ?
        """,
        (normalized_code,),
    ).fetchone()


def _requirement_row_by_code(connection: sqlite3.Connection, req_code: str):
    normalized_req_code = _normalize_required_text(req_code, "req_code")
    return connection.execute(
        """
        SELECT id, req_code, title, category_id, description, status, created_at, updated_at
        FROM project_requirements
        WHERE req_code = ?
        """,
        (normalized_req_code,),
    ).fetchone()


def init_history_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS requirement_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                req_code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('proposed', 'active', 'completed', 'dropped')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES requirement_categories(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS requirement_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_id INTEGER NOT NULL,
                prompt_text TEXT NOT NULL,
                execution_summary TEXT NOT NULL,
                execution_impact TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (requirement_id) REFERENCES project_requirements(id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_requirements_category_id
            ON project_requirements(category_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_requirement_execution_requirement_id
            ON requirement_execution(requirement_id)
            """
        )

        created_at = _utc_now()
        connection.executemany(
            """
            INSERT OR IGNORE INTO requirement_categories (code, name, description, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (code, name, description, created_at)
                for code, name, description in INITIAL_CATEGORY_SEEDS
            ],
        )
        connection.commit()


def list_requirement_categories() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, code, name, description, created_at
            FROM requirement_categories
            ORDER BY id ASC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def create_requirement_category(*, code: str, name: str, description: str | None = None) -> dict:
    normalized_code = _normalize_required_text(code, "code")
    normalized_name = _normalize_required_text(name, "name")
    normalized_description = description.strip() if isinstance(description, str) and description.strip() else None

    with _connect() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO requirement_categories (code, name, description, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (normalized_code, normalized_name, normalized_description, _utc_now()),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Could not create requirement category: {exc}") from exc

        row = connection.execute(
            """
            SELECT id, code, name, description, created_at
            FROM requirement_categories
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_dict(row)


def create_project_requirement(
    *,
    req_code: str,
    title: str,
    category_code: str,
    description: str,
    status: str = "proposed",
) -> dict:
    normalized_req_code = _normalize_required_text(req_code, "req_code")
    normalized_title = _normalize_required_text(title, "title")
    normalized_description = _normalize_required_text(description, "description")
    normalized_status = _normalize_required_text(status, "status")

    if normalized_status not in ALLOWED_REQUIREMENT_STATUSES:
        raise ValueError("status must be one of: proposed, active, completed, dropped.")

    with _connect() as connection:
        category_row = _category_row_by_code(connection, category_code)
        if not category_row:
            raise ValueError(f"Unknown requirement category: {category_code}")

        now = _utc_now()
        try:
            cursor = connection.execute(
                """
                INSERT INTO project_requirements (
                    req_code,
                    title,
                    category_id,
                    description,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_req_code,
                    normalized_title,
                    category_row["id"],
                    normalized_description,
                    normalized_status,
                    now,
                    now,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Could not create project requirement: {exc}") from exc

        row = connection.execute(
            """
            SELECT id, req_code, title, category_id, description, status, created_at, updated_at
            FROM project_requirements
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_dict(row)


def create_requirement_execution(
    *,
    req_code: str,
    prompt_text: str,
    execution_summary: str,
    execution_impact: str,
) -> dict:
    normalized_prompt_text = _normalize_required_text(prompt_text, "prompt_text")
    normalized_summary = _normalize_required_text(execution_summary, "execution_summary")
    normalized_impact = _normalize_required_text(execution_impact, "execution_impact")

    with _connect() as connection:
        requirement_row = _requirement_row_by_code(connection, req_code)
        if not requirement_row:
            raise ValueError(f"Unknown project requirement: {req_code}")

        try:
            cursor = connection.execute(
                """
                INSERT INTO requirement_execution (
                    requirement_id,
                    prompt_text,
                    execution_summary,
                    execution_impact,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    requirement_row["id"],
                    normalized_prompt_text,
                    normalized_summary,
                    normalized_impact,
                    _utc_now(),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Could not create requirement execution: {exc}") from exc

        row = connection.execute(
            """
            SELECT id, requirement_id, prompt_text, execution_summary, execution_impact, created_at
            FROM requirement_execution
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_dict(row)


def ensure_requirement_category(*, code: str, name: str | None = None, description: str | None = None) -> dict:
    with _connect() as connection:
        existing_row = _category_row_by_code(connection, code)
    if existing_row:
        return _row_to_dict(existing_row)

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Category '{code}' does not exist and category_name is required to create it.")

    return create_requirement_category(code=code, name=name, description=description)


def ensure_project_requirement(
    *,
    req_code: str,
    title: str | None = None,
    category_code: str,
    description: str | None = None,
    status: str = "active",
) -> dict:
    with _connect() as connection:
        existing_row = _requirement_row_by_code(connection, req_code)
    if existing_row:
        return _row_to_dict(existing_row)

    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Requirement '{req_code}' does not exist and title is required to create it.")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"Requirement '{req_code}' does not exist and description is required to create it.")

    return create_project_requirement(
        req_code=req_code,
        title=title,
        category_code=category_code,
        description=description,
        status=status,
    )


def list_requirements_by_category(category_code: str) -> list[dict]:
    with _connect() as connection:
        category_row = _category_row_by_code(connection, category_code)
        if not category_row:
            raise ValueError(f"Unknown requirement category: {category_code}")

        rows = connection.execute(
            """
            SELECT id, req_code, title, category_id, description, status, created_at, updated_at
            FROM project_requirements
            WHERE category_id = ?
            ORDER BY id ASC
            """,
            (category_row["id"],),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_requirement_execution(req_code: str) -> list[dict]:
    with _connect() as connection:
        requirement_row = _requirement_row_by_code(connection, req_code)
        if not requirement_row:
            raise ValueError(f"Unknown project requirement: {req_code}")

        rows = connection.execute(
            """
            SELECT id, requirement_id, prompt_text, execution_summary, execution_impact, created_at
            FROM requirement_execution
            WHERE requirement_id = ?
            ORDER BY id ASC, created_at ASC
            """,
            (requirement_row["id"],),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_execution_history_with_labels(*, req_code: str | None = None) -> list[dict]:
    query = """
        SELECT
            re.id AS execution_id,
            pr.req_code AS requirement_code,
            pr.title AS requirement_title,
            rc.code AS category_code,
            rc.name AS category_name,
            re.execution_summary,
            re.execution_impact,
            re.prompt_text,
            re.created_at
        FROM requirement_execution re
        INNER JOIN project_requirements pr ON pr.id = re.requirement_id
        INNER JOIN requirement_categories rc ON rc.id = pr.category_id
    """
    params: tuple = ()
    if req_code:
        query += " WHERE pr.req_code = ?"
        params = (_normalize_required_text(req_code, "req_code"),)
    query += " ORDER BY re.id ASC, re.created_at ASC"

    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def commit_requirement_execution(
    *,
    req_code: str,
    category_code: str,
    category_name: str | None,
    category_description: str | None,
    requirement_title: str | None,
    requirement_description: str | None,
    requirement_status: str,
    commit_message: str,
    prompt_text: str,
    execution_summary: str,
    execution_impact: str,
) -> dict:
    ensure_requirement_category(
        code=category_code,
        name=category_name,
        description=category_description,
    )
    requirement = ensure_project_requirement(
        req_code=req_code,
        title=requirement_title,
        category_code=category_code,
        description=requirement_description,
        status=requirement_status,
    )

    subprocess.run(
        ["git", "add", "--all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    execution = create_requirement_execution(
        req_code=req_code,
        prompt_text=prompt_text,
        execution_summary=execution_summary,
        execution_impact=execution_impact,
    )

    return {
        "commit_hash": commit_hash,
        "requirement": requirement,
        "execution": execution,
    }
