from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Mapping


def resolve_chromium_executable(
    *,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    is_file: Callable[[str], bool] = lambda candidate: Path(candidate).is_file(),
) -> str | None:
    environment = os.environ if environ is None else environ
    explicit = environment.get("PIPELINE_CHROMIUM_EXECUTABLE", "").strip()
    if explicit and is_file(explicit):
        return explicit

    for command in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        candidate = which(command)
        if candidate and is_file(candidate):
            return candidate
    return None
