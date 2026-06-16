import os

from dotenv import load_dotenv

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


class Agent:
    def __init__(self) -> None:
        self.cwd = Path.cwd()

        chat = ChatOllama(model="gemma4-128k:latest", temperature=0.5)
        tools = build_file_tools(self.cwd)
        self._avail_tools = {t.name: t for t in tools}
        self.model = chat.bind_tools(tools=tools)

        self.messages: list[BaseMessage] = [
            SystemMessage(self.get_sys_prompt())
        ]
    
    def get_work_dir(self):
        return self.cwd

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
                result = tool.invoke(args)
                status = "success"
            except Exception as e:
                result = (
                    f"Error during tool execution: {type(e).__name__}: {str(e)}"
                )
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
