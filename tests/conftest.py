"""Test-suite-wide environment defaults.

Sets dummy access tokens so the startup check in ``app/main.py``'s
lifespan passes during tests. Individual API tests monkeypatch
``settings.*`` per test; this only guarantees the *startup* path
doesn't crash before the monkeypatch can apply.
"""

import os

os.environ.setdefault("CHAT_ACCESS_TOKEN", "test-startup-chat-token")
os.environ.setdefault("ADMIN_TOKEN", "test-startup-admin-token")
