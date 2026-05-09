"""Async data-access layer.

The only place in the codebase that runs SQL (per CLAUDE.md § Layering).
Schema lives in `alembic/`; module-level async functions in passages.py
provide typed read/write access against an AsyncSession opened from the
factory in db.py.
"""
