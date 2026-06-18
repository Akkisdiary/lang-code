import difflib
from typing import Any


from .ansi import Colors as ANSI
from langchain_core.messages import (
    AIMessage,
    ToolCall,
    ToolMessage,
)

PREVIEW_LEN = 64


class TUI:
    """Handles all console rendering"""

    def prompt_user(self):
        return input(f"{ANSI.GREEN}> User: {ANSI.END}")

    def display_hint(self, message: str):
        print(f"{ANSI.FAINT} {message}{ANSI.END}")

    def display_user_input(self, message: Any):
        print(f"{ANSI.GREEN}> User: {message}{ANSI.END}")

    def display_ai_message(self, message: AIMessage):
        reasoning = message.additional_kwargs.get("reasoning_content")
        if reasoning:
            print(
                f"{ANSI.CYAN}> AI: {ANSI.END}"
                f"{ANSI.FAINT}Reasoning...\n{reasoning}{ANSI.END}"
            )
        if message.content:
            print(f"{ANSI.CYAN}> AI: {ANSI.END}{message.content}")
        if message.tool_calls:
            for tc in message.tool_calls:
                self.display_tool_call(tc)

    def display_tool_call(self, tool_call: ToolCall):
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})

        if tool_name == "edit_file":
            file_path = args.get("path")
            print(f">> {ANSI.YELLOW}{tool_name}({file_path}){ANSI.END}")
            self.display_diff(args["old_string"], args["new_string"])
        elif tool_name == "read_file":
            file_path = args.get("path")
            print(f">> {ANSI.YELLOW}{tool_name}({file_path}){ANSI.END}")
        else:
            # Standard display for other tool calls
            sargs = str(args)
            sargs = (
                sargs[:PREVIEW_LEN] + "..."
                if len(sargs) > PREVIEW_LEN
                else sargs
            )
            print(f">> {ANSI.YELLOW}{tool_name}({sargs}){ANSI.END}")

    def display_diff(self, old_string: str, new_string: str):
        old_lines = old_string.splitlines(keepends=True)
        new_lines = new_string.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                for line in old_lines[i1:i2]:
                    print(f"{ANSI.RED}- {line}{ANSI.END}")
            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    print(f"{ANSI.GREEN}+ {line}{ANSI.END}")
            elif tag == "replace":
                for line in old_lines[i1:i2]:
                    print(f"{ANSI.RED}- {line}{ANSI.END}")
                for line in new_lines[j1:j2]:
                    print(f"{ANSI.GREEN}+ {line}{ANSI.END}")
            else:
                for line in old_lines[i1:i2]:
                    print(f"{ANSI.CYAN}  {line}{ANSI.END}")

    def display_tool_result(self, message: ToolMessage):
        lines = str(message.content).strip().split("\n")
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
