"""Tech Scout Agent - Technology evaluation and scouting."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path("research/tech-scout")

EVALUATION_CRITERIA = [
    "Fit - Does it solve a real project need?",
    "Maturity - Production-ready or bleeding edge?",
    "Maintenance - Active community and updates?",
    "Integration - Easy to fit into existing stack?",
    "Performance - Benchmarks vs alternatives?",
    "License - Compatible with project license?",
]


class TechScoutAgent(BaseReActAgent):
    """Technology scout evaluating new tools and frameworks.

    Research outputs:
    - Technology evaluations
    - Landscape overviews
    - Selection decisions with trade-offs
    """

    def __init__(self, llm: Any | None = None):
        system_prompt = self._load_prompt()
        super().__init__(
            agent_id="tech_scout",
            name="Tech Scout",
            role="research",
            system_prompt=system_prompt,
        )
        self.llm = llm
        self._ensure_research_dir()

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/system/tech_scout.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "Evaluate technologies and produce selection reports."

    def _ensure_research_dir(self) -> None:
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    async def think(self, state: AgentState) -> str:
        """Analyze tech evaluation request."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")

        # Determine domain
        query_lower = query.lower()
        if any(w in query_lower for w in ["frontend", "ui", "vue", "react", "svelte"]):
            domain = "frontend"
        elif any(w in query_lower for w in ["backend", "api", "fastapi", "database"]):
            domain = "backend"
        elif any(w in query_lower for w in ["ai", "ml", "model", "llm", "vector"]):
            domain = "ai-ml"
        elif any(w in query_lower for w in ["devops", "ci", "cd", "deploy", "docker"]):
            domain = "devops"
        else:
            domain = "general"

        return f"Domain: {domain} | Query: '{query[:50]}' | Date: {today}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Evaluate technology and generate reports."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")
        domain = thought.split("Domain: ")[1].split("|")[0].strip()

        # Extract technology name from query
        tech_name = self._extract_tech_name(query)

        # Generate evaluation
        evaluation = await self._evaluate_tech(tech_name, domain, query)

        # Write report
        eval_path = RESEARCH_DIR / f"{tech_name}-evaluation-{today}.md"
        eval_path.write_text(evaluation["evaluation"])

        # Update landscape if applicable
        landscape_path = RESEARCH_DIR / f"{domain}-landscape-{today}.md"
        landscape_path.write_text(evaluation["landscape"])

        logger.info(
            "TechScout: evaluated %s (%s), report at %s",
            tech_name,
            domain,
            RESEARCH_DIR,
        )

        return {
            "technology": tech_name,
            "domain": domain,
            "evaluation_path": str(eval_path),
            "landscape_path": str(landscape_path),
            "recommendation": evaluation["recommendation"],
            "metadata": {"_finished": True, "_stub": True, "_stub_reason": "Technology evaluation not integrated - returns placeholder data"},
        }

    def _extract_tech_name(self, query: str) -> str:
        """Extract technology name from query."""
        # Simple extraction - in production use NLP
        words = query.split()
        # Look for capitalized technology names
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                return word.lower().replace("-", "_")
        # Fallback: first significant word
        for word in words:
            if word.lower() not in ["evaluate", "compare", "vs", "research", "the", "a"]:
                return word.lower().replace("-", "_")
        return "unknown-tech"

    async def _evaluate_tech(
        self, tech_name: str, domain: str, query: str
    ) -> dict[str, str]:
        """Evaluate a specific technology."""
        from agents.research_tools import search_tech_docs, search_alternatives

        # Gather information
        docs = await search_tech_docs(tech_name, limit=5)
        alternatives = await search_alternatives(tech_name, limit=3)

        # Build evaluation
        evaluation = self._build_evaluation(tech_name, domain, docs, alternatives)
        landscape = self._build_landscape(domain, tech_name, alternatives)
        recommendation = self._get_recommendation(evaluation)

        return {
            "evaluation": evaluation,
            "landscape": landscape,
            "recommendation": recommendation,
        }

    def _build_evaluation(
        self,
        tech_name: str,
        domain: str,
        docs: list[dict],
        alternatives: list[dict],
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Technology Evaluation: {tech_name.upper()}",
            f"**Domain**: {domain}",
            f"**Date**: {today}",
            "",
            "## Overview",
            f"[stub] Overview not available - technology search not integrated",
            "",
            "## Evaluation Criteria",
            "",
        ]

        for criterion in EVALUATION_CRITERIA:
            lines.append(f"### {criterion}")
            lines.append("- [ ] **Fit**: [stub]")
            lines.append("- [ ] **Maturity**: [stub]")
            lines.append("- [ ] **Maintenance**: [stub]")
            lines.append("- [ ] **Integration**: [stub]")
            lines.append("- [ ] **Performance**: [stub]")
            lines.append("- [ ] **License**: [stub]")
            lines.append("")

        lines.extend(["## Documentation", ""])
        for doc in docs:
            lines.append(f"- [{doc['title']}]({doc['url']})")

        lines.extend(["", "## Alternatives Compared", ""])
        for alt in alternatives:
            lines.append(f"- {alt['name']}: [stub] comparison not available")

        lines.extend(["", "## When TO Use", "", "- [stub] Use cases not available", ""])
        lines.extend(["", "## When NOT to Use", "", "- [stub] Avoid cases not available", ""])

        lines.append("---")
        lines.append(f"*Generated by Tech Scout Agent on {today}*")
        return "\n".join(lines)

    def _build_landscape(self, domain: str, main_tech: str, alternatives: list[dict]) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# {domain.upper()} Technology Landscape",
            f"**Date**: {today}",
            "",
            "## Overview",
            f"Landscape analysis for {domain} domain, focusing on {main_tech}.",
            "",
            "## Competitors",
            "",
        ]

        for alt in alternatives:
            lines.append(f"### {alt['name']}")
            lines.append(f"- **Strengths**: [stub]")
            lines.append(f"- **Weaknesses**: [stub]")
            lines.append(f"- **Best for**: [stub]")
            lines.append("")

        lines.extend(["", "## Trends", "", "- [stub] Domain trends not available", ""])
        lines.extend(["", "## Recommendations", "", "- [stub] Strategic recommendations not available", ""])
        return "\n".join(lines)

    def _get_recommendation(self, evaluation: str) -> str:
        """Extract recommendation from evaluation."""
        # Simple heuristic - in production use LLM
        if "High Priority" in evaluation:
            return "adopt"
        elif "avoid" in evaluation.lower():
            return "avoid"
        return "evaluate-further"


def create_tech_scout(llm: Any = None) -> TechScoutAgent:
    """Factory function to create TechScoutAgent."""
    return TechScoutAgent(llm=llm)
