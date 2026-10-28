"""shell pack: run commands and Python. Opt-in — only loaded if you ask for "shell"."""
from __future__ import annotations

import asyncio
import contextlib
import io

from ..tools import tool


@tool
async def run_command(command: str, timeout: int = 60) -> dict:
    """Run a shell command and return stdout, stderr and exit code."""
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"error": f"timed out after {timeout}s"}
    return {"stdout": out.decode(errors="replace")[-8000:], "stderr": err.decode(errors="replace")[-4000:],
            "code": proc.returncode}


@tool
def run_python(code: str) -> str:
    """Execute Python code in-process and return whatever it prints."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            exec(code, {"__name__": "__nobelagentic__"})
        except Exception as e:  # noqa: BLE001
            print(f"{type(e).__name__}: {e}")
    return buf.getvalue()[-8000:] or "(no output)"


TOOLS = [run_command, run_python]
