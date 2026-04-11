"""AI Researcher Agent - Research AI/ML/LangGraph/LLM topics."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path("research/ai-researcher")


class AIResearcherAgent(BaseReActAgent):
    """AI/ML Researcher specializing in LangGraph and Multi-Agent systems.

    Research outputs:
    - Detailed technical reports
    - Executive summaries
    - Implementation recommendations
    """

    def __init__(self, llm: Any | None = None):
        system_prompt = self._load_prompt()
        super().__init__(
            agent_id="ai_researcher",
            name="AI Researcher",
            role="research",
            system_prompt=system_prompt,
        )
        self.llm = llm
        self._ensure_research_dir()

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/system/ai_researcher.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "Research AI/ML topics and produce technical reports."

    def _ensure_research_dir(self) -> None:
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    async def think(self, state: AgentState) -> str:
        """Analyze research request and plan approach."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")

        # Determine research type from query
        query_lower = query.lower()
        if "langgraph" in query_lower or "langchain" in query_lower:
            topic = "langgraph"
        elif "multi-agent" in query_lower or "agent" in query_lower:
            topic = "multi-agent"
        elif "reasoning" in query_lower or "reason" in query_lower:
            topic = "llm-reasoning"
        elif "model" in query_lower or "llm" in query_lower:
            topic = "llm"
        else:
            topic = "ai-general"

        return f"Research topic: {topic} | Query: '{query[:50]}' | Date: {today}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Conduct research and generate report."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")
        topic = thought.split("topic: ")[1].split("|")[0].strip()

        # Generate report path
        report_path = RESEARCH_DIR / f"{topic}-report-{today}.md"
        summary_path = RESEARCH_DIR / f"{topic}-summary-{today}.md"
        action_path = RESEARCH_DIR / f"{topic}-action-items-{today}.md"

        # Conduct web research
        findings = await self._research_topic(topic, query)

        # Write reports
        report_path.write_text(findings["report"])
        summary_path.write_text(findings["summary"])
        action_path.write_text(findings["actions"])

        logger.info(
            "AIResearcher: completed %s research, reports at %s",
            topic,
            RESEARCH_DIR,
        )

        return {
            "research_topic": topic,
            "report_path": str(report_path),
            "summary_path": str(summary_path),
            "action_items_path": str(action_path),
            "findings": findings["summary"],
            "metadata": {"_finished": True, "_stub": True, "_stub_reason": "Web search not integrated - returns placeholder data"},
        }

    async def _research_topic(self, topic: str, query: str) -> dict[str, str]:
        """Conduct research on the given topic using web search."""
        from agents.research_tools import search_papers, search_blogs, get_trending_topics

        # Get trending topics and recent papers/blogs
        trending = get_trending_topics(topic)
        papers = await search_papers(topic, limit=5)
        blogs = await search_blogs(topic, limit=5)

        # Build report
        report = self._build_report(topic, query, trending, papers, blogs)
        summary = self._build_summary(topic, trending)
        actions = self._build_action_items(topic, papers, blogs)

        return {
            "report": report,
            "summary": summary,
            "actions": actions,
        }

    def _build_report(
        self,
        topic: str,
        query: str,
        trending: list[dict],
        papers: list[dict],
        blogs: list[dict],
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# AI Research Report: {topic.upper()}",
            f"**Date**: {today}",
            f"**Query**: {query}",
            "",
            "## Trending Topics",
            "",
        ]

        for item in trending[:5]:
            lines.append(f"- **{item['title']}**: {item['description']}")

        lines.extend(["", "## Recent Papers", ""])
        for paper in papers:
            lines.append(
                f"- [{paper['title']}]({paper['url']}) - {paper.get('venue', 'arXiv')}"
            )

        lines.extend(["", "## Recent Blog Posts", ""])
        for blog in blogs:
            lines.append(f"- [{blog['title']}]({blog['url']}) - {blog.get('source', 'Blog')}")

        lines.extend(["", "## Analysis", "", "[stub] Detailed analysis not available - web search not integrated", ""])
        lines.extend(["", "## Code Examples", "", "[stub] Code examples not available - web search not integrated", ""])
        lines.append("---")
        lines.append(f"*Generated by AI Researcher Agent on {today}*")
        return "\n".join(lines)

    def _build_summary(self, topic: str, trending: list[dict]) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Summary: {topic.upper()}",
            f"**Date**: {today}",
            "",
            "## Key Takeaways",
            "",
        ]
        for item in trending[:3]:
            lines.append(f"- {item['title']}: {item['description']}")
        lines.append("")
        lines.append("## Recommendations")
        lines.append("- [stub] Specific recommendations not available - web search not integrated")
        return "\n".join(lines)

    def _build_action_items(self, topic: str, papers: list[dict], blogs: list[dict]) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Action Items: {topic.upper()}",
            f"**Date**: {today}",
            "",
            "## Implementation Recommendations",
            "",
            "### High Priority",
            "- [ ] [stub] High priority action not available",
            "",
            "### Medium Priority",
            "- [ ] [stub] Medium priority action not available",
            "",
            "### Low Priority",
            "- [ ] [stub] Low priority action not available",
            "",
            "## Read Next",
        ]
        for paper in papers[:3]:
            lines.append(f"- [ ] Read: {paper['title']}")
        return "\n".join(lines)


def create_ai_researcher(llm: Any = None) -> AIResearcherAgent:
    """Factory function to create AIResearcherAgent."""
    return AIResearcherAgent(llm=llm)
