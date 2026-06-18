from typing import Any

from .ansi import Colors as ANSI
from langchain_core.messages import ToolCall


PREVIEW_LEN = 64


class TUI:
    """Handles all console rendering"""

    def prompt_user(self):
        return input(f"{ANSI.GREEN}> User: {ANSI.END}")

    def display_hint(self, content: str):
        print(f"{ANSI.FAINT} {content}{ANSI.END}")

    def display_user_input(self, content: Any):
        print(f"\n{ANSI.GREEN}> User: {content}{ANSI.END}")

    def display_ai_message(self, content: Any):
        print(f"\n{ANSI.CYAN}> AI: {ANSI.END}", end="", flush=True)
        print(content)

    def display_tool_call(self, tool_call: ToolCall):
        tool_name = tool_call.get("name")
        sargs = str(tool_call.get("args"))
        sargs = (
            sargs[PREVIEW_LEN:] + "..."
            if len(sargs) > PREVIEW_LEN
            else sargs
        )
        print(f">> {ANSI.YELLOW}{tool_name}({sargs}){ANSI.END}")

    def display_tool_result(self, content: Any):
        lines = str(content).strip().split("\n")
        first_line = lines[0]
        displayed_content = first_line[:PREVIEW_LEN]
        total_lines = len(lines)

        # Construct the minimal preview string: "Preview... +N lines"
        preview_text = (
            displayed_content
            if len(first_line) <= PREVIEW_LEN
            else f"{displayed_content}..."
        )
        output = (
            f"{ANSI.FAINT}{preview_text} +{total_lines - 1} lines{ANSI.END}"
        )
        print(output)

    def display_error(self, message: str):
        print(f"{ANSI.RED}{ANSI.END}{message}")

    def display_warning(self, message: str):
        print(f"{ANSI.LIGHT_RED}{message}{ANSI.END}")
