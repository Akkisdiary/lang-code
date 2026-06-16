# src/cli_chat/tui_handler.py

import sys
from typing import Any

from .ansi import Colors as ANSI


class TUI:
    """Handles all console rendering"""

    def prompt_user(self):
        return input(f"{ANSI.GREEN}> User: {ANSI.END}")

    def display_hint(self, content: str):
        print(f"{ANSI.FAINT} {content}{ANSI.END}")

    def display_user_input(self, content: Any):
        """Displays the current user message."""
        print(f"\n{ANSI.GREEN}> User: {content}{ANSI.END}")

    def display_ai_message(self, content: Any):
        """Streams or displays AI response text."""
        # Use a subtle color for the AI output
        print(f"\n{ANSI.CYAN}> AI: {ANSI.END}", end="", flush=True)
        print(content)

    def display_tool_call_info(self, tool_name: str, args: dict):
        """Shows when the agent decides to use a tool."""
        # Tool calls are important context, make them stand out.
        sargs = str(args)
        sargs = args[:64] + "..." if len(sargs) > 64 else ""
        print(
            f"\n{ANSI.YELLOW}[AGENT] Calling Tool: {tool_name}({sargs}){ANSI.END}"
        )

    def display_tool_result(self, content: Any):
        """Displays the output received from an executed tool, truncating for preview."""
        # Use a distinct color for machine/system results.
        print(
            f"\n{ANSI.YELLOW}[TOOL RESULT]: {ANSI.END}",
            end="",
            flush=True,
        )

        MAX_PREVIEW_LENGTH = 128

        if len(content) > MAX_PREVIEW_LENGTH:
            truncated_content = content[:MAX_PREVIEW_LENGTH]
            print(f"{truncated_content}\n...\n")
        else:
            print(content)

    def display_error(self, message: str):
        """Displays critical errors or warnings."""
        # Use the error color and write to stderr for best practice.
        print(
            f"\n{ANSI.RED}[ERROR]{ANSI.END} {message}",
            file=sys.stderr,
        )
