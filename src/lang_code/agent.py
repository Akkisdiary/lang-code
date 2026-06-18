import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import json

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    messages_to_dict,
    messages_from_dict,
    BaseMessage,
)
from langchain_ollama import ChatOllama

from .file_tools import build_file_tools


class AgentSession:
    def __init__(
        self,
        system_prompt: SystemMessage | None = None,
    ) -> None:
        self.session_history_path = (
            Path(".agents") / "session" / "conversation_history.json"
        )

        if system_prompt:
            self.conversation: list[BaseMessage] = [system_prompt]
        else:
            self.conversation = []

    def load(self):
        if not self.session_history_path.exists():
            return
        try:
            with open(self.session_history_path, "r") as f:
                history = json.load(f)
                self.conversation.extend(messages_from_dict(history))
        except json.JSONDecodeError:
            print(
                "Warning: Could not decode conversation history file. Starting fresh."
            )
        except Exception as e:
            print(f"Error loading history: {e}. Starting fresh.")

    def save(self):
        self.session_history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.session_history_path, "w") as f:
                json.dump(
                    messages_to_dict(self.conversation), f
                )  # Don't store the system prompt
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_human_message(self, message: str):
        self.conversation.append(HumanMessage(message))

    def add_ai_msg(self, msg: str | AIMessage) -> None:
        if isinstance(msg, AIMessage):
            self.conversation.append(msg)
        else:
            self.conversation.append(AIMessage(msg))

    def add_tool_msg(self, msg: ToolMessage) -> None:
        self.conversation.append(msg)


class Agent:
    def __init__(
        self,
        model: str = "gemma4-128k:latest",
    ) -> None:
        self.cwd = Path.cwd()
        tools = build_file_tools(self.cwd)
        self._avail_tools = {t.name: t for t in tools}
        self.model = ChatOllama(model=model, temperature=0.5).bind_tools(
            tools=tools
        )

        self.session = AgentSession(self.get_sys_prompt())
        self.session.load()

    def get_work_dir(self):
        return self.cwd

    def get_sys_prompt(self):
        with open(os.path.join(self.cwd, "AGENTS.md")) as f:
            prompt = f.read().strip()
        prompt.replace("<<_LC_CWD>>", str(self.get_work_dir()))
        return SystemMessage(prompt)

    async def exec_tool(self, tool_call: ToolCall) -> ToolMessage:
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

    async def ainvoke(self, message: str):
        self.session.add_human_message(message)

        try:
            while True:
                if not self.session.conversation:
                    return
                res: AIMessage = await self.model.ainvoke(
                    self.session.conversation
                )
                self.session.add_ai_msg(res)
                yield res

                if res.tool_calls:
                    for tool_call in res.tool_calls:
                        tool_message = await self.exec_tool(tool_call)
                        self.session.add_tool_msg(tool_message)
                        yield tool_message
                else:
                    break
        finally:
            self.session.save()
