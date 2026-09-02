from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs"


def resolve_executable(env_name: str, command: str, *candidates: str) -> Path:
    """Resolve a renderer from an explicit override, PATH, or known install location."""
    override = os.environ.get(env_name)
    if override:
        return Path(override).expanduser()
    discovered = shutil.which(command)
    if discovered:
        return Path(discovered)
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return Path(command)


MATLAB_EXE = resolve_executable("HENGMO_MATLAB_EXE", "matlab")
XELATEX_EXE = resolve_executable("HENGMO_XELATEX_EXE", "xelatex")
DVISVGM_EXE = resolve_executable("HENGMO_DVISVGM_EXE", "dvisvgm")
VISIO_EXE = resolve_executable(
    "HENGMO_VISIO_EXE",
    "VISIO.EXE",
    r"C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\VISIO.EXE",
)


def ensure_dir(path: str | os.PathLike[str] | None) -> Path:
    target = Path(path) if path else DEFAULT_OUTPUT
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def safe_basename(name: str, fallback: str = "figure") -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", str(name)).strip(" .")
    return cleaned or fallback


def run_process(command: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    """Run a renderer without allowing its timeout to tear down the MCP request.

    Renderer servers need a structured failure result so they can report partial artifacts and
    provenance honestly. The caller's timeout should remain below the transport deadline.
    """
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "command": command,
            "returncode": 124,
            "timed_out": True,
            "timeout_seconds": timeout,
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
        }
    return {
        "command": command,
        "returncode": completed.returncode,
        "timed_out": False,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def file_manifest(paths: list[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in paths:
        if path.exists():
            result.append({
                "path": str(path.resolve()),
                "size": path.stat().st_size,
                "suffix": path.suffix.lower(),
            })
    return result


def json_result(**kwargs: Any) -> str:
    return json.dumps(kwargs, ensure_ascii=False, indent=2)


def escape_tex(text: Any) -> str:
    value = str(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def rgb_tuple(value: Any, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(value, str):
        value = value.strip().lstrip("#")
        if len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value):
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(max(0, min(255, int(x))) for x in value)  # type: ignore[return-value]
    return default


def visio_rgb_formula(value: Any, default: tuple[int, int, int]) -> str:
    r, g, b = rgb_tuple(value, default)
    return f"RGB({r},{g},{b})"


def matlab_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def points(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    out: list[list[float]] = []
    for item in value:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append([number(item[0]), number(item[1])])
    return out


def json_dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
