"""GenericAgentRunner - Prompt 驱动的通用 Agent 执行器

核心思想：Agent 行为完全由 prompt 配置决定，无需为每个任务写 Python 类。

ReAct Pattern:
    Thought → Action → Observation → ... → Output
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from dataclasses import dataclass

from core.models import AgentState
from core.minimax_client import MiniMaxClient, get_minimax_client
from agents.base.prompt_loader import PromptLoader, load_prompt_with_frontmatter

logger = logging.getLogger(__name__)


@dataclass
class ReActConfig:
    """ReAct 循环配置"""
    max_iterations: int = 10
    finish_condition: str = "max_iterations"  # max_iterations | confidence_threshold
    finish_value: float = 0.7


@dataclass
class AgentConfig:
    """Agent 配置 (从 markdown frontmatter 解析)"""
    agent_id: str
    name: str
    role: str
    output_schema: Optional[str] = None  # 输出格式类型
    tools: Optional[list[str]] = None  # 可用工具列表
    react: Optional[ReActConfig] = None
    prompt_file: Optional[str] = None  # prompt 文件路径


class GenericAgentRunner:
    """
    通用 Agent 执行器

    使用方式:
        runner = GenericAgentRunner.from_prompt_file("prompts/system/intent_agent.md")
        result = await runner.run("用户查询")
    """

    def __init__(
        self,
        config: AgentConfig,
        system_prompt: str,
        llm_client: Optional[MiniMaxClient] = None,
        tools: Optional[list[Any]] = None,
    ):
        self.config = config
        self.system_prompt = system_prompt
        self.llm = llm_client or get_minimax_client()
        self.tools = tools or []
        self.prompt_loader = PromptLoader()

    @classmethod
    def from_prompt_file(
        cls,
        prompt_file: str,
        llm_client: Optional[MiniMaxClient] = None,
        variables: Optional[dict[str, Any]] = None,
    ) -> "GenericAgentRunner":
        """
        从 prompt 文件加载 Agent

        Args:
            prompt_file: prompt 文件路径 (如 prompts/system/intent_agent.md)
            llm_client: LLM 客户端
            variables: 额外的变量替换
        """
        # 加载 prompt 和配置
        frontmatter, body = load_prompt_with_frontmatter(
            prompt_file,
            variables=variables,
        )

        if not frontmatter:
            raise ValueError(f"No frontmatter found in {prompt_file}")

        # 解析 react 配置
        react_config = None
        if "react" in frontmatter:
            r = frontmatter["react"]
            react_config = ReActConfig(
                max_iterations=r.get("max_iterations", 10),
                finish_condition=r.get("finish_condition", "max_iterations"),
                finish_value=r.get("finish_value", 0.7),
            )

        # 构建 AgentConfig
        config = AgentConfig(
            agent_id=frontmatter.get("agent_id", ""),
            name=frontmatter.get("name", ""),
            role=frontmatter.get("role", "L0"),
            output_schema=frontmatter.get("output_schema"),
            tools=frontmatter.get("tools"),
            react=react_config,
            prompt_file=prompt_file,
        )

        return cls(
            config=config,
            system_prompt=body,
            llm_client=llm_client,
        )

    async def think(self, state: AgentState) -> str:
        """
        Reasoning step - 调用 LLM 进行推理

        Args:
            state: 当前 Agent 状态

        Returns:
            推理结果字符串
        """
        messages = self._build_messages(state)

        response = await self.llm.chat(
            messages=messages,
            tools=self._get_tool_schemas(),
        )

        # 从响应中提取文本内容
        return self._extract_content(response)

    def _extract_content(self, response: dict[str, Any]) -> str:
        """从 LLM 响应中提取文本内容"""
        # 尝试从 choices[0].message.content 提取
        choices = response.get("choices", [])
        if choices and len(choices) > 0:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    if content:
                        return content

        # 尝试直接从 response 提取
        if "content" in response:
            return response["content"]

        return str(response)

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """
        Action step - 解析 LLM 响应，执行工具调用

        Args:
            state: 当前 Agent 状态
            thought: 推理结果

        Returns:
            状态更新字典
        """
        # 解析 thought 中的工具调用
        # 格式: ToolName(arg1="value1", arg2="value2")
        tool_calls = self._parse_tool_calls(thought)

        results = []
        for tool_name, tool_args in tool_calls:
            result = await self._execute_tool(tool_name, tool_args)
            results.append(result)

        return {
            "tool_results": results,
            "last_thought": thought,
        }

    def _should_finish(self, state: AgentState) -> bool:
        """检查是否应该结束 ReAct 循环"""
        react = self.config.react
        if not react:
            return len(state.messages) >= 20

        if react.finish_condition == "max_iterations":
            return len(state.messages) >= react.max_iterations * 2

        # confidence_threshold 逻辑可以后续扩展
        return len(state.messages) >= react.max_iterations * 2

    async def run(self, input: str) -> dict[str, Any]:
        """
        运行 Agent - 完整的 ReAct 循环

        Args:
            input: 用户输入

        Returns:
            最终结果字典
        """
        state = AgentState(
            user_query=input,
            messages=[],
            metadata={"agent_id": self.config.agent_id},
        )

        iteration = 0
        thought = ""
        max_iter = self.config.react.max_iterations if self.config.react else 10

        while iteration < max_iter:
            # Think
            thought = await self.think(state)

            # 检查是否应该结束
            if self._should_finish(state):
                break

            # Act
            updates = await self.act(state, thought)

            # 更新状态
            state.messages.append({
                "role": "assistant",
                "content": thought,
                "agent_id": self.config.agent_id,
            })

            iteration += 1

        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "output": thought if iteration > 0 else "",
            "iterations": iteration,
            "state": state,
        }

    def _build_messages(self, state: AgentState) -> list[dict[str, Any]]:
        """构建 LLM 消息"""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        # 添加历史消息
        for msg in state.messages[-10:]:  # 最近 10 条
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # 添加当前查询
        if state.user_query:
            messages.append({
                "role": "user",
                "content": state.user_query,
            })

        return messages

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """获取工具 schema 列表"""
        if not self.tools:
            return []

        schemas = []
        for tool in self.tools:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                schemas.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": getattr(tool, "input_schema", {}),
                })
        return schemas

    def _parse_tool_calls(self, thought: str) -> list[tuple[str, dict[str, Any]]]:
        """
        解析 thought 中的工具调用

        当前简单实现，后续可以扩展支持更复杂的格式

        Returns:
            [(tool_name, {args}), ...]
        """
        import re

        tool_calls = []
        # 匹配格式: ToolName(arg1="value1", arg2="value2")
        pattern = r'(\w+)\s*\(\s*(.*?)\s*\)'

        for match in re.finditer(pattern, thought):
            tool_name = match.group(1)
            args_str = match.group(2)

            # 简单解析参数
            args = self._parse_args(args_str)

            tool_calls.append((tool_name, args))

        return tool_calls

    def _parse_args(self, args_str: str) -> dict[str, Any]:
        """解析参数字符串"""
        import re
        import json

        args = {}

        # 匹配 key="value" 或 key=value 格式
        pattern = r'(\w+)\s*=\s*["\']?([^"\',\)]+)["\']?'

        for match in re.finditer(pattern, args_str):
            key = match.group(1)
            value = match.group(2).strip()

            # 尝试转换为适当类型
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                value = float(value)

            args[key] = value

        return args

    async def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """执行工具调用"""
        # 查找工具
        tool = None
        for t in self.tools:
            if hasattr(t, "name") and t.name == tool_name:
                tool = t
                break

        if not tool:
            return {"error": f"Tool not found: {tool_name}"}

        try:
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(args)
            elif hasattr(tool, "invoke"):
                result = tool.invoke(args)
            else:
                result = tool(args)

            return {"tool": tool_name, "result": result}
        except Exception as e:
            return {"tool": tool_name, "error": str(e)}


# 工厂函数
async def create_agent_from_prompt(
    prompt_file: str,
    llm_client: Optional[MiniMaxClient] = None,
    tools: Optional[list[Any]] = None,
    variables: Optional[dict[str, Any]] = None,
) -> GenericAgentRunner:
    """从 prompt 文件创建 Agent"""
    return GenericAgentRunner.from_prompt_file(
        prompt_file=prompt_file,
        llm_client=llm_client,
        variables=variables,
    )
