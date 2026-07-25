"""Development entrypoint:  python run.py

For production use a process manager instead:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
"""

from __future__ import annotations

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=not settings.is_production,
        log_config=None,  # app.core.logging owns logging configuration
    )
