from .agent import Agent
from .tui import TUI
from langchain_core.messages import AIMessage, ToolMessage


def main():
    agent = Agent()
    tui = TUI()

    try:
        while True:
            user_msg = tui.prompt_user()

            if not user_msg.strip():
                continue

            for res in agent.invoke(user_msg):
                if isinstance(res, AIMessage) and res.content:
                    tui.display_ai_message(res.content)
                elif isinstance(res, ToolMessage):
                    tui.display_tool_result(res.content)

    except KeyboardInterrupt:
        tui.display_hint("\n\nChat interupted by user.")


if __name__ == "__main__":
    main()
