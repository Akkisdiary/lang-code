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
                if isinstance(res, AIMessage):
                    if res.content:
                        tui.display_ai_message(res.content)
                    if res.tool_calls:
                        for tc in res.tool_calls:
                            tui.display_tool_call(tc)
                elif isinstance(res, ToolMessage):
                    tui.display_tool_result(res.content)
                else:
                    tui.display_warning(f"Unknown msg type: {res}")

    except KeyboardInterrupt:
        tui.display_warning("\nChat interupted by user.")


if __name__ == "__main__":
    main()
