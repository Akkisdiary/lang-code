# src/cli_chat/tui_handler.py

import sys
from typing import Any


class ChatRenderer:
    """
    Handles all console rendering for the chat agent using ANSI colors
    for a modern, minimal look.
    """

    # ANSI Color Codes
    COLOR_RESET = "\033[0m"
    COLOR_SYSTEM = "\033[94m"  # Blue
    COLOR_USER = "\033[92m"  # Green
    COLOR_AI = "\033[96m"  # Cyan
    COLOR_TOOL = "\033[93m"  # Yellow
    COLOR_ERROR = "\033[91m"  # Red

    def __init__(self):
        pass

    def display_system_prompt(self, prompt: str):
        """Displays initial system instructions in a distinct block."""
        print("\n" + "=" * 60)
        print(
            f"{self.COLOR_SYSTEM}SYSTEM INSTRUCTIONS LOADED{self.COLOR_RESET}"
        )
        print("=" * 60)
        # Use standard text for the prompt content itself, but frame it with color
        print(prompt)
        print("-" * 60 + "\n")

    def display_user_input(self, user: Any):
        """Displays the current user message."""
        print(f"\n{self.COLOR_USER}> User: {user}{self.COLOR_RESET}")

    def display_ai_message(self, content: Any):
        """Streams or displays AI response text."""
        # Use a subtle color for the AI output
        print(f"\n{self.COLOR_AI}> AI: {self.COLOR_RESET}", end="", flush=True)
        print(content)

    def display_tool_call_info(self, tool_name: str, args: dict):
        """Shows when the agent decides to use a tool."""
        # Tool calls are important context, make them stand out.
        sargs = str(args)
        sargs = args[:64] + "..." if len(sargs) > 64 else ""
        print(
            f"\n{self.COLOR_TOOL}[AGENT] Calling Tool: {tool_name}({sargs}){self.COLOR_RESET}"
        )

    def display_tool_result(self, content: Any):
        """Displays the output received from an executed tool, truncating for preview."""
        # Use a distinct color for machine/system results.
        print(
            f"\n{self.COLOR_TOOL}[TOOL RESULT]: {self.COLOR_RESET}",
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
            f"\n{self.COLOR_ERROR}[ERROR]{self.COLOR_RESET} {message}",
            file=sys.stderr,
        )


# Global instance for easy access in main loop
renderer = ChatRenderer()
