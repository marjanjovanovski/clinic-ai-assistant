import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "project_history.db"
REPO_ROOT = BASE_DIR.parent
ALLOWED_REQUIREMENT_STATUSES = {"proposed", "active", "completed", "dropped"}
ALLOWED_LESSON_STATUSES = {"proposed", "validated", "obsolete"}
INITIAL_CATEGORY_SEEDS = (
    ("security", "Security", "Security-related project requirements."),
    ("gui", "GUI", "User interface and presentation requirements."),
    ("business_logic", "Business Logic", "Core business rules and backend behavior."),
    ("infrastructure", "Infrastructure", "Platform, environment, and operational infrastructure."),
    ("documentation", "Documentation", "Documentation and sync artifact requirements."),
    ("lessons_learned_repo", "Lessons Learned", "Lessons learned repository and project memory requirements."),
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


def _execution_rows_by_ids(connection: sqlite3.Connection, execution_ids: list[int]):
    if not execution_ids:
        raise ValueError("At least one execution_id is required.")

    placeholders = ",".join("?" for _ in execution_ids)
    rows = connection.execute(
        f"""
        SELECT id, requirement_id, prompt_text, execution_summary, execution_impact, git_commit_hash, created_at
        FROM requirement_execution
        WHERE id IN ({placeholders})
        ORDER BY id ASC
        """,
        tuple(execution_ids),
    ).fetchall()
    if len(rows) != len(set(execution_ids)):
        found_ids = {row["id"] for row in rows}
        missing_ids = [execution_id for execution_id in execution_ids if execution_id not in found_ids]
        raise ValueError(f"Unknown execution ids: {missing_ids}")
    return rows


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
                git_commit_hash TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (requirement_id) REFERENCES project_requirements(id)
            )
            """
        )
        execution_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(requirement_execution)").fetchall()
        }
        if "git_commit_hash" not in execution_columns:
            connection.execute(
                """
                ALTER TABLE requirement_execution
                ADD COLUMN git_commit_hash TEXT
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons_learned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_code TEXT NOT NULL UNIQUE,
                requirement_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                statement TEXT NOT NULL,
                why_it_matters TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('proposed', 'validated', 'obsolete')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (requirement_id) REFERENCES project_requirements(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_execution_links (
                lesson_id INTEGER NOT NULL,
                execution_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (lesson_id, execution_id),
                FOREIGN KEY (lesson_id) REFERENCES lessons_learned(id),
                FOREIGN KEY (execution_id) REFERENCES requirement_execution(id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lessons_learned_requirement_id
            ON lessons_learned(requirement_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lesson_execution_links_execution_id
            ON lesson_execution_links(execution_id)
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

        # Migrate the previous category in place instead of duplicating it.
        connection.execute(
            """
            UPDATE requirement_categories
            SET code = ?, name = ?, description = ?
            WHERE code = 'data'
            """,
            (
                "lessons_learned_repo",
                "Lessons Learned",
                "Lessons learned repository and project memory requirements.",
            ),
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
    git_commit_hash: str | None = None,
) -> dict:
    normalized_prompt_text = _normalize_required_text(prompt_text, "prompt_text")
    normalized_summary = _normalize_required_text(execution_summary, "execution_summary")
    normalized_impact = _normalize_required_text(execution_impact, "execution_impact")
    normalized_commit_hash = git_commit_hash.strip() if isinstance(git_commit_hash, str) and git_commit_hash.strip() else None

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
                    git_commit_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    requirement_row["id"],
                    normalized_prompt_text,
                    normalized_summary,
                    normalized_impact,
                    normalized_commit_hash,
                    _utc_now(),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Could not create requirement execution: {exc}") from exc

        row = connection.execute(
            """
            SELECT id, requirement_id, prompt_text, execution_summary, execution_impact, git_commit_hash, created_at
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
            SELECT id, requirement_id, prompt_text, execution_summary, execution_impact, git_commit_hash, created_at
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
            re.git_commit_hash,
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


def create_lesson_learned(
    *,
    lesson_code: str,
    title: str,
    statement: str,
    why_it_matters: str,
    source_execution_ids: list[int],
    status: str = "validated",
) -> dict:
    normalized_lesson_code = _normalize_required_text(lesson_code, "lesson_code")
    normalized_title = _normalize_required_text(title, "title")
    normalized_statement = _normalize_required_text(statement, "statement")
    normalized_why = _normalize_required_text(why_it_matters, "why_it_matters")
    normalized_status = _normalize_required_text(status, "status")

    if normalized_status not in ALLOWED_LESSON_STATUSES:
        raise ValueError("status must be one of: proposed, validated, obsolete.")

    normalized_execution_ids = []
    for execution_id in source_execution_ids:
        try:
            normalized_execution_ids.append(int(execution_id))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid execution id: {execution_id}") from exc

    with _connect() as connection:
        execution_rows = _execution_rows_by_ids(connection, normalized_execution_ids)
        requirement_ids = {row["requirement_id"] for row in execution_rows}
        if len(requirement_ids) != 1:
            raise ValueError("All source execution ids must belong to the same requirement.")

        existing_row = connection.execute(
            """
            SELECT id FROM lessons_learned WHERE lesson_code = ?
            """,
            (normalized_lesson_code,),
        ).fetchone()
        if existing_row:
            raise ValueError(f"Lesson code already exists: {normalized_lesson_code}")

        now = _utc_now()
        cursor = connection.execute(
            """
            INSERT INTO lessons_learned (
                lesson_code,
                requirement_id,
                title,
                statement,
                why_it_matters,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_lesson_code,
                next(iter(requirement_ids)),
                normalized_title,
                normalized_statement,
                normalized_why,
                normalized_status,
                now,
                now,
            ),
        )
        lesson_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO lesson_execution_links (lesson_id, execution_id, created_at)
            VALUES (?, ?, ?)
            """,
            [
                (lesson_id, row["id"], now)
                for row in execution_rows
            ],
        )
        connection.commit()

        lesson_row = connection.execute(
            """
            SELECT id, lesson_code, requirement_id, title, statement, why_it_matters, status, created_at, updated_at
            FROM lessons_learned
            WHERE id = ?
            """,
            (lesson_id,),
        ).fetchone()
    return _row_to_dict(lesson_row)


def list_lessons_with_labels(*, lesson_code: str | None = None) -> list[dict]:
    query = """
        SELECT
            ll.id AS lesson_id,
            ll.lesson_code,
            ll.title AS lesson_title,
            ll.statement,
            ll.why_it_matters,
            ll.status AS lesson_status,
            pr.req_code AS requirement_code,
            pr.title AS requirement_title,
            rc.code AS category_code,
            rc.name AS category_name,
            GROUP_CONCAT(lel.execution_id, ', ') AS source_execution_ids,
            ll.created_at,
            ll.updated_at
        FROM lessons_learned ll
        INNER JOIN project_requirements pr ON pr.id = ll.requirement_id
        INNER JOIN requirement_categories rc ON rc.id = pr.category_id
        INNER JOIN lesson_execution_links lel ON lel.lesson_id = ll.id
    """
    params: tuple = ()
    if lesson_code:
        query += " WHERE ll.lesson_code = ?"
        params = (_normalize_required_text(lesson_code, "lesson_code"),)
    query += """
        GROUP BY
            ll.id,
            ll.lesson_code,
            ll.title,
            ll.statement,
            ll.why_it_matters,
            ll.status,
            pr.req_code,
            pr.title,
            rc.code,
            rc.name,
            ll.created_at,
            ll.updated_at
        ORDER BY ll.id ASC
    """
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
        git_commit_hash=commit_hash,
    )

    return {
        "commit_hash": commit_hash,
        "requirement": requirement,
        "execution": execution,
    }
