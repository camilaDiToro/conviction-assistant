"""Business logic.

Services orchestrate repositories, parsers, and (later) providers. They
raise domain exceptions (defined in app/errors.py); they never raise
HTTPException or reference HTTP status codes — that's the API layer's job.
"""
