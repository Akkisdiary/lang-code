import os

from dotenv import load_dotenv
from prompt_toolkit import PromptSession

load_dotenv()

from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    BaseMessage,
)
from langchain_ollama import ChatOllama

from .file_tools import build_file_tools
from .tui import renderer


class Agent:
    def __init__(self) -> None:
        self.cwd = Path.cwd()
        print("CWD:", self.cwd)

        chat = ChatOllama(model="gemma4-128k:latest", temperature=0.5)
        tools = build_file_tools(self.cwd)
        self._avail_tools = {t.name: t for t in tools}
        self.model = chat.bind_tools(tools=tools)

        self.messages: list[BaseMessage] = [
            SystemMessage(self.get_sys_prompt())
        ]

    def get_sys_prompt(self):
        with open(os.path.join(self.cwd, "AGENTS.md")) as f:
            return f.read().strip()

    def _add_human_msg(self, msg: str) -> None:
        self.messages.append(HumanMessage(msg))

    def _add_ai_msg(self, msg: str | AIMessage) -> None:
        if isinstance(msg, AIMessage):
            self.messages.append(msg)
        else:
            self.messages.append(AIMessage(msg))

    def _add_tool_msg(self, msg: ToolMessage) -> None:
        self.messages.append(msg)

    def exec_tool(self, tool_call: ToolCall) -> ToolMessage:
        tool_name = tool_call.get("name")
        tool = self._avail_tools.get(tool_name)
        status = "error"
        if tool is None:
            result = f"error: unknown tool '{tool_name}'"
        else:
            try:
                args = tool_call.get("args", {})
                renderer.display_tool_call_info(tool_name, args)
                result = tool.invoke(args)
                status = "success"
            except Exception as e:
                result = f"runtime error during execution: {type(e).__name__}: {str(e)}"
        return ToolMessage(
            name=tool_name,
            content=result,
            tool_call_id=tool_call["id"],
            status=status,
        )

    def invoke(self, message: str):
        self._add_human_msg(message)

        while True:
            if not self.messages:
                return
            res: AIMessage = self.model.invoke(self.messages)
            self._add_ai_msg(res)
            yield res

            if res.tool_calls:
                for tool_call in res.tool_calls:
                    yield tool_call
                    tool_message = self.exec_tool(tool_call)
                    self._add_tool_msg(tool_message)
                    yield tool_message
            else:
                return


def main():
    agent = Agent()
    session = PromptSession()

    try:
        while True:
            user_msg = session.prompt("User: ")

            if not user_msg.strip():
                continue

            renderer.display_user_input(user_msg)

            for res in agent.invoke(user_msg):
                if isinstance(res, AIMessage) and res.content:
                    renderer.display_ai_message(res.content)
                elif isinstance(res, ToolMessage):
                    renderer.display_tool_result(res.content)

    except KeyboardInterrupt:
        renderer.display_error("Chat interupted by user.")


if __name__ == "__main__":
    main()
