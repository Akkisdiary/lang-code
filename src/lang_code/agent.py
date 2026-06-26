import os
import uuid
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .tools.fs import build_file_tools

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Agent:
    def __init__(
        self,
        model: str = "gemma4-128k:latest",
        thinking: str | bool | None = "low",
    ) -> None:
        self.cwd = Path.cwd()
        self.config_dir = self.cwd / ".agents"
        self.sessions_dir = self.config_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        tools = build_file_tools(self.cwd)
        self._avail_tools = {t.name: t for t in tools}

        self.config: RunnableConfig = {
            "configurable": {"thread_id": str(uuid.uuid4())}
        }
        system_prompt = self.get_sys_prompt()
        self.model = ChatOllama(
            model=model,
            temperature=0.4,
            reasoning=thinking,
        )
        self.conn = aiosqlite.connect(self.sessions_dir / "session.sqlite")
        self.checkpoint = AsyncSqliteSaver(self.conn)
        self._agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=self.checkpoint,
        )

    def get_sys_prompt(self):
        with open(os.path.join(BASE_DIR, "prompts/SYSTEM.md"), "r") as f:
            system_prompt = f.read().strip()
        system_prompt = system_prompt.replace("<<_LC_CWD>>", str(self.cwd))
        return SystemMessage(system_prompt)

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
                result = f"Error executing tool {tool_name}: {e}"
        return ToolMessage(
            name=tool_name,
            content=result,
            tool_call_id=tool_call["id"],
            status=status,
        )

    async def ainvoke(self, message: str):
        return await self._agent.ainvoke(
            {"messages": [HumanMessage(message)]},
            config=self.config,
        )

    async def astream_events(self, message: str):
        return await self._agent.astream_events(
            {"messages": [HumanMessage(message)]},
            config=self.config,
            version="v3",
        )

    async def cleanup(self):
        """Saves the conversation history when the agent session ends."""
        await self.conn.close()
