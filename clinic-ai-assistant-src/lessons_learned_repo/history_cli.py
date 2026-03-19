import argparse
import json
from pathlib import Path

from lessons_learned_repo.history_store import (
    commit_requirement_execution,
    create_lesson_learned,
    create_project_requirement,
    create_requirement_category,
    create_requirement_execution,
    init_history_db,
    list_execution_history_with_labels,
    list_lessons_with_labels,
    list_requirement_categories,
    list_requirement_execution,
    list_requirements_by_category,
)


def _read_prompt_text(args) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt_text


def _print_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lessons learned repository trigger entrypoint for requirement-linked execution records."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="Create the project history database and seed categories.")
    init_db.set_defaults(handler=lambda args: {"status": "initialized"})

    add_category = subparsers.add_parser("create-category", help="Create a requirement category.")
    add_category.add_argument("--code", required=True)
    add_category.add_argument("--name", required=True)
    add_category.add_argument("--description")
    add_category.set_defaults(
        handler=lambda args: create_requirement_category(
            code=args.code,
            name=args.name,
            description=args.description,
        )
    )

    add_requirement = subparsers.add_parser("create-requirement", help="Create a project requirement.")
    add_requirement.add_argument("--req-code", required=True)
    add_requirement.add_argument("--title", required=True)
    add_requirement.add_argument("--category-code", required=True)
    add_requirement.add_argument("--description", required=True)
    add_requirement.add_argument("--status", default="proposed")
    add_requirement.set_defaults(
        handler=lambda args: create_project_requirement(
            req_code=args.req_code,
            title=args.title,
            category_code=args.category_code,
            description=args.description,
            status=args.status,
        )
    )

    add_execution = subparsers.add_parser(
        "record-execution",
        help="Trigger entry for requirement-linked repo-changing execution history.",
    )
    add_execution.add_argument("--req-code", required=True)
    add_execution.add_argument("--prompt-text")
    add_execution.add_argument("--prompt-file")
    add_execution.add_argument("--summary", required=True)
    add_execution.add_argument("--impact", required=True)
    add_execution.set_defaults(
        handler=lambda args: create_requirement_execution(
            req_code=args.req_code,
            prompt_text=_read_prompt_text(args),
            execution_summary=args.summary,
            execution_impact=args.impact,
        )
    )

    commit_with_history = subparsers.add_parser(
        "commit-with-history",
        help="Commit repo changes and record the execution against a requirement.",
    )
    commit_with_history.add_argument("--req-code", required=True)
    commit_with_history.add_argument("--category-code", required=True)
    commit_with_history.add_argument("--category-name")
    commit_with_history.add_argument("--category-description")
    commit_with_history.add_argument("--title")
    commit_with_history.add_argument("--description")
    commit_with_history.add_argument("--status", default="active")
    commit_with_history.add_argument("--commit-message", required=True)
    commit_with_history.add_argument("--prompt-text")
    commit_with_history.add_argument("--prompt-file")
    commit_with_history.add_argument("--summary", required=True)
    commit_with_history.add_argument("--impact", required=True)
    commit_with_history.set_defaults(
        handler=lambda args: commit_requirement_execution(
            req_code=args.req_code,
            category_code=args.category_code,
            category_name=args.category_name,
            category_description=args.category_description,
            requirement_title=args.title,
            requirement_description=args.description,
            requirement_status=args.status,
            commit_message=args.commit_message,
            prompt_text=_read_prompt_text(args),
            execution_summary=args.summary,
            execution_impact=args.impact,
        )
    )

    list_categories = subparsers.add_parser("list-categories", help="List requirement categories.")
    list_categories.set_defaults(handler=lambda args: list_requirement_categories())

    list_requirements = subparsers.add_parser("list-requirements", help="List requirements by category.")
    list_requirements.add_argument("--category-code", required=True)
    list_requirements.set_defaults(
        handler=lambda args: list_requirements_by_category(args.category_code)
    )

    list_executions = subparsers.add_parser("list-executions", help="List execution history by requirement.")
    list_executions.add_argument("--req-code", required=True)
    list_executions.set_defaults(
        handler=lambda args: list_requirement_execution(args.req_code)
    )

    list_labeled_history = subparsers.add_parser(
        "list-history",
        help="List execution history with joined requirement and category labels.",
    )
    list_labeled_history.add_argument("--req-code")
    list_labeled_history.set_defaults(
        handler=lambda args: list_execution_history_with_labels(req_code=args.req_code)
    )

    create_lesson = subparsers.add_parser(
        "create-lesson",
        help="Create a curated lesson linked to one or more execution ids.",
    )
    create_lesson.add_argument("--lesson-code", required=True)
    create_lesson.add_argument("--title", required=True)
    create_lesson.add_argument("--statement", required=True)
    create_lesson.add_argument("--why-it-matters", required=True)
    create_lesson.add_argument("--execution-ids", nargs="+", required=True)
    create_lesson.add_argument("--status", default="validated")
    create_lesson.set_defaults(
        handler=lambda args: create_lesson_learned(
            lesson_code=args.lesson_code,
            title=args.title,
            statement=args.statement,
            why_it_matters=args.why_it_matters,
            source_execution_ids=args.execution_ids,
            status=args.status,
        )
    )

    list_lessons = subparsers.add_parser(
        "list-lessons",
        help="List curated lessons with requirement/category labels and source execution ids.",
    )
    list_lessons.add_argument("--lesson-code")
    list_lessons.set_defaults(
        handler=lambda args: list_lessons_with_labels(lesson_code=args.lesson_code)
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    init_history_db()

    if args.command in {"record-execution", "commit-with-history"} and not (args.prompt_text or args.prompt_file):
        parser.error(f"{args.command} requires --prompt-text or --prompt-file")

    result = args.handler(args)
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
