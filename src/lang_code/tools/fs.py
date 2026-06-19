"""File CRUD tools sandboxed to a working directory.

All paths are resolved against `workdir` and rejected with a clear
error if they escape the sandbox. This keeps the model from reading or writing arbitrary files
on disk.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


def _resolve(workdir: Path, raw_path: str) -> Path:
    """Resolve `raw_path` against `workdir` and ensure it stays inside."""
    candidate = (workdir / raw_path).resolve()
    workdir_resolved = workdir.resolve()
    try:
        # Check if the candidate path is a subpath of the working directory root
        candidate.relative_to(workdir_resolved)
    except ValueError as exc:
        raise ValueError(
            f"path '{raw_path}' escapes the working directory "
            f"'{workdir_resolved}'"
        ) from exc
    return candidate


def build_file_tools(workdir: str | os.PathLike[str]) -> list:
    """Create the file CRUD tools bound to `workdir`."""
    root = Path(workdir).resolve()
    # Ensure the sandbox root exists when tools are built
    root.mkdir(parents=True, exist_ok=True)

    @tool
    def read(
        path: Annotated[str, "Path relative to the working directory"],
    ) -> str:
        """Read the contents of a text file. Returns an error string if the file is missing, not a regular file, or larger than 1 MB."""
        target = _resolve(root, path)
        if not target.exists():
            return f"'{path}' does not exist"
        if not target.is_file():
            return f"'{path}' is not a regular file"
        if target.stat().st_size > 1_000_000:
            return f"'{path}' is larger than 1 MB; refusing to read"
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"'{path}' is not a UTF-8 text file"

    @tool
    def edit(
        path: Annotated[str, "Path relative to the working directory"],
        old_string: Annotated[str, "String to find and replace."],
        new_string: Annotated[str, "New string to insert."],
    ) -> str:
        """
        Performs exact string replacements in files.
        Usage:
        - When editing text from read_file tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears.
        - This tools works finding & replacing old_string in the file. ALWAYS prefer editing a file in small chunks to avoid miss match due to trivial error.
        """

        target = _resolve(root, path)

        if not target.exists():
            raise ValueError(f"'{path}' does not exist.")
        if not target.is_file():
            raise ValueError(f"'{path}' is not a file; cannot edit.")

        if not old_string and not new_string:
            raise ValueError("both old_string & new_string cannot be empty")

        if not old_string:
            raise ValueError("old_string cannot be empty")

        if not new_string:
            raise ValueError("new_string cannot be empty")

        try:
            original_content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"'{path}' is not a UTF-8 text file.")

        if old_string not in original_content:
            raise ValueError(
                f"old_string not present in {target.relative_to(root)}."
            )

        new_content = original_content.replace(old_string, new_string)

        try:
            target.write_text(new_content, encoding="utf-8")
            return f"Successfully replaced all occurrences of '{old_string}' with '{new_string}' in {target.relative_to(root)}."
        except Exception as e:
            raise ValueError(f"error writing file: {e}")

    @tool
    def glob(
        path: Annotated[str, "Path relative to the working directory"],
        pattern: Annotated[str, "Glob pattern (e.g., '*.py', '**/*.js')."],
    ) -> str:
        """Find all files matching a given glob pattern within the specified path."""
        target = _resolve(root, path)
        if not target.exists():
            raise ValueError(f"'{path}' does not exist")

        # Use rglob for recursive search if the pattern suggests it (e.g., contains **)
        try:
            found_paths = list(target.rglob(pattern))
        except Exception as e:
            return f"Error executing glob pattern '{pattern}': {e}"

        if not found_paths:
            return "No files found matching the pattern."

        results: list[str] = []
        for p in found_paths:
            # Only report paths that are actual files, and ensure they are within the sandbox
            relative_path = str(p.relative_to(root))
            if p.is_dir():
                results.append(f"[dir] {relative_path}")
            elif p.is_file():
                results.append(f"[file] {relative_path}")
            else:
                results.append(f"[unknown] {relative_path}")

        return "\n".join(sorted(results))

    @tool
    def bash(
        command: Annotated[
            str, "The shell command to execute (e.g., 'ls -l', 'git status')."
        ],
    ) -> str:
        """
        Executes a system shell command in the current working directory.
        WARNING: This tool executes arbitrary code and bypasses file sandboxing. Use with extreme caution.
        Output includes stdout followed by stderr if any errors occur.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                cwd=root,
            )
            return (
                f"STDOUT:\n{result.stdout}\n\nSTDERR (if any):\n{result.stderr}"
            )
        except subprocess.CalledProcessError as e:
            return f"ERROR executing command '{command}':\nReturn Code: {e.returncode}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        except Exception as e:
            return f"CRITICAL ERROR during shell execution: {str(e)}"

    return [
        read,
        edit,
        glob,
        bash,
    ]
