"""Entrypoint for the optional residential rendered-HTML service."""

from __future__ import annotations

import os

from src.residential_service import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("RESIDENTIAL_FETCHER_HOST", "0.0.0.0"),
        port=int(os.getenv("RESIDENTIAL_FETCHER_PORT", "8765")),
        log_level="info",
    )
