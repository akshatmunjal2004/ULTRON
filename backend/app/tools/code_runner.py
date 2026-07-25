"""Run a short Python snippet in a child process.

Read this before switching it on. Executing model-generated code is inherently
dangerous: the snippet runs with the same file access and network access as the
API process. The mitigations here raise the cost of an accident, they do not
make this a sandbox:

  * off unless ENABLE_CODE_EXECUTION is true
  * the REST route that reaches it requires an API key
  * CPU, address space, file size and process count are capped with setrlimit
  * the child runs in a throwaway directory with a scrubbed environment
  * a wall-clock timeout kills the whole process group

For anything multi-tenant or internet-facing, run the snippet in a container or
a microVM (gVisor, Firecracker, Docker with --network=none) instead of here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from pydantic import BaseModel, Field

from app.core.config import settings
from app.tools.base import BaseTool

MAX_CODE_CHARS = 10_000
MAX_OUTPUT_CHARS = 8_000


class CodeRunnerParams(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)


def _limits() -> object:
    """Return a preexec_fn applying rlimits, or None where unsupported."""
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return None

    cpu = max(1, settings.CODE_EXECUTION_TIMEOUT)
    memory = settings.CODE_EXECUTION_MEMORY_MB * 1024 * 1024

    # The process group is created by start_new_session=True, not here: calling
    # setsid() in preexec_fn as well fails with EPERM and aborts the spawn.
    caps = [
        (resource.RLIMIT_CPU, (cpu, cpu)),
        (resource.RLIMIT_AS, (memory, memory)),
        (resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024)),
        (resource.RLIMIT_NPROC, (64, 64)),
        (resource.RLIMIT_CORE, (0, 0)),
    ]

    def apply() -> None:
        for which, values in caps:
            try:
                resource.setrlimit(which, values)
            except (ValueError, OSError):
                # A limit the kernel or container does not allow us to set is
                # not a reason to refuse to run at all.
                continue

    return apply


class CodeRunnerTool(BaseTool):
    name = "code_runner"
    description = (
        "Execute a short Python snippet and return whatever it prints. Use it for "
        "calculations and small data tasks. Always print() the result."
    )
    params_model = CodeRunnerParams
    requires_auth = True

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_CODE_EXECUTION

    @property
    def disabled_reason(self) -> str:
        return (
            "Code execution is switched off. Set ENABLE_CODE_EXECUTION=true in the "
            "backend .env to allow it, and only on a machine you control."
        )

    def execute(self, params: CodeRunnerParams) -> str:
        workdir = tempfile.mkdtemp(prefix="ultron-exec-")
        script = os.path.join(workdir, "snippet.py")
        timeout = settings.CODE_EXECUTION_TIMEOUT

        try:
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(params.code)

            proc = subprocess.run(  # noqa: S603 - inputs are fixed, code is a file arg
                [sys.executable, "-I", "-S", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
                env={"PATH": "/usr/bin:/bin", "HOME": workdir, "PYTHONIOENCODING": "utf-8"},
                preexec_fn=_limits(),  # noqa: PLW1509 - intentional, see module docstring
                start_new_session=True,
            )
        except subprocess.TimeoutExpired:
            return f"The snippet was still running after {timeout}s, so it was stopped."
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        out = (proc.stdout or "").strip()[:MAX_OUTPUT_CHARS]
        err = (proc.stderr or "").strip()[:MAX_OUTPUT_CHARS]

        if err and out:
            return f"Output:\n{out}\n\nErrors:\n{err}"
        if err:
            return f"Errors:\n{err}"
        return out or "The snippet ran but printed nothing."
