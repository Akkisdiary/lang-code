"""File CRUD tools sandboxed to a working directory.

All paths are resolved against `workdir` and rejected with a clear
error if they escape the sandbox. This keeps the model from reading or writing arbitrary files
on disk.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
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
    def read_file(
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
    def write_file(
        path: Annotated[str, "Path relative to the working directory"],
        content: Annotated[str, "The full text content to write."],
    ) -> str:
        """Create or overwrite a text file with the given content. Creates parent directories as needed."""
        target = _resolve(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {target.relative_to(root)}"

    @tool
    def list_dir(
        path: Annotated[str, "Path relative to the working directory"] = ".",
    ) -> str:
        """List the immediate contents of a directory (names + type marker)."""
        target = _resolve(root, path)
        if not target.exists():
            raise ValueError(f"'{path}' does not exist")
        if not target.is_dir():
            raise ValueError(f"'{path}' is not a directory")
        entries: list[str] = []
        for child in sorted(target.iterdir()):
            if child.is_dir():
                entries.append(f"[dir]  {child.name}")
            elif child.is_file():
                entries.append(f"[file] {child.name}")
            else:
                entries.append(f"[?]    {child.name}")
        if not entries:
            return "(empty directory)"
        return "\n".join(entries)

    @tool
    def delete_file(
        path: Annotated[str, "Path relative to the working directory"],
    ) -> str:
        """Delete a file or empty directory."""
        target = _resolve(root, path)
        if not target.exists():
            raise ValueError(f"'{path}' does not exist")
        if target.is_dir():
            raise ValueError(
                f"'{path}' is a directory; use delete_dir_recursive "
                "to remove it"
            )
        target.unlink()
        return f"deleted {target.relative_to(root)}"

    @tool
    def delete_dir_recursive(
        path: Annotated[str, "Path relative to the working directory"],
    ) -> str:
        """Recursively delete a directory and all of its contents."""
        target = _resolve(root, path)
        if not target.exists():
            raise ValueError("'{path}' does not exist")
        if not target.is_dir():
            raise ValueError("'{path}' is not a directory")
        if target == root:
            raise ValueError("refusing to delete the working directory root")
        shutil.rmtree(target)
        return f"removed directory {target.relative_to(root)}"

    @tool
    def file_info(
        path: Annotated[str, "Path relative to the working directory."],
    ) -> str:
        """Return existence, type, size (bytes) and modification time for a path."""
        target = _resolve(root, path)
        if not target.exists():
            raise ValueError(f"'{path}' does not exist")
        stat = target.stat()
        kind = (
            "directory"
            if target.is_dir()
            else "file" if target.is_file() else "other"
        )
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat(
            timespec="seconds"
        )
        return (
            f"exists: True\n"
            f"type: {kind}\n"
            f"size_bytes: {stat.st_size}\n"
            f"modified: {mtime}\n"
            f"path: {target.relative_to(root)}"
        )

    @tool
    def edit_file(
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

        try:
            original_content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"'{path}' is not a UTF-8 text file.")

        if old_string == "" and new_string == "":
            raise ValueError("both strings empty. No change made.")

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

    return [
        read_file,
        write_file,
        list_dir,
        delete_file,
        delete_dir_recursive,
        file_info,
        edit_file,
    ]
