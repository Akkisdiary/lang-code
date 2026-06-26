import asyncio
import traceback

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .agent import Agent
from .tui import TUI


async def run():
    agent = Agent(
        model="gemma4-128k:latest",
        thinking="high",
        # persist_session=False,
    )
    tui = TUI()

    try:
        while True:
            user_msg = tui.prompt_user()

            if not user_msg.strip():
                continue

            stream = await agent.astream_events(user_msg)
            async for snapshot in stream.values:
                latest = snapshot["messages"][-1]
                if latest.content:
                    if isinstance(latest, AIMessage):
                        tui.display_ai_message(latest)
                    elif isinstance(latest, ToolMessage):
                        tui.display_tool_result(latest)
                    elif isinstance(latest, HumanMessage):
                        # tui.display_human_message(latest)
                        pass
                    else:
                        tui.display_warning(
                            f"Unknown msg type: {type(latest)}: {latest}"
                        )
                elif latest.tool_calls:
                    for tool_call in latest.tool_calls:
                        tui.display_tool_call(tool_call)
                else:
                    tui.display_warning(
                        f"Unkown snapshot: {type(snapshot)} - {snapshot}"
                    )

    except KeyboardInterrupt:
        tui.display_warning("\nChat interrupted by user.")
    finally:
        await agent.cleanup()


def main():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
    except Exception:
        print("Error in main loop")
        traceback.print_exc()


if __name__ == "__main__":
    main()
