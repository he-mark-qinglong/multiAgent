"""Process Optimizer Agent - Team workflow analysis and optimization."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.langgraph_agents import BaseReActAgent
from core.models import AgentState

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path("research/process-optimizer")


class ProcessOptimizerAgent(BaseReActAgent):
    """Process optimizer analyzing and improving team workflows.

    Outputs:
    - Workflow analyses
    - Tool design documents
    - Automation scripts
    - Templates
    """

    def __init__(self, llm: Any | None = None):
        system_prompt = self._load_prompt()
        super().__init__(
            agent_id="process_optimizer",
            name="Process Optimizer",
            role="research",
            system_prompt=system_prompt,
        )
        self.llm = llm
        self._ensure_research_dir()

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/system/process_optimizer.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "Analyze workflows and produce optimization reports."

    def _ensure_research_dir(self) -> None:
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        (RESEARCH_DIR / "templates").mkdir(parents=True, exist_ok=True)
        (RESEARCH_DIR / "tools").mkdir(parents=True, exist_ok=True)

    async def think(self, state: AgentState) -> str:
        """Analyze process improvement request."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")

        # Determine focus area
        query_lower = query.lower()
        if "workflow" in query_lower or "process" in query_lower:
            focus = "workflow"
        elif "template" in query_lower:
            focus = "template"
        elif "automation" in query_lower or "script" in query_lower:
            focus = "automation"
        elif "measure" in query_lower or "metric" in query_lower:
            focus = "measurement"
        else:
            focus = "general"

        return f"Focus: {focus} | Query: '{query[:50]}' | Date: {today}"

    async def act(self, state: AgentState, thought: str) -> dict[str, Any]:
        """Analyze and optimize workflow."""
        query = state.user_query
        today = datetime.now().strftime("%Y-%m-%d")
        focus = thought.split("Focus: ")[1].split("|")[0].strip()

        process_name = self._extract_process_name(query)

        # Analyze and generate improvement
        analysis = await self._analyze_process(process_name, focus, query)

        # Write analysis
        analysis_path = RESEARCH_DIR / f"{process_name}-analysis-{today}.md"
        analysis_path.write_text(analysis["analysis"])

        # Write improvement plan
        improvement_path = RESEARCH_DIR / f"{process_name}-improvement-{today}.md"
        improvement_path.write_text(analysis["improvement"])

        # Generate templates if needed
        templates = {}
        if focus in ["template", "workflow"]:
            templates = await self._generate_templates(process_name)

        # Generate automation scripts if needed
        scripts = {}
        if focus in ["automation", "workflow"]:
            scripts = await self._generate_automation(process_name, analysis)

        logger.info(
            "ProcessOptimizer: analyzed %s (%s), reports at %s",
            process_name,
            focus,
            RESEARCH_DIR,
        )

        return {
            "process_name": process_name,
            "focus": focus,
            "analysis_path": str(analysis_path),
            "improvement_path": str(improvement_path),
            "templates": templates,
            "scripts": scripts,
            "impact_score": analysis["impact_score"],
            "metadata": {"_finished": True, "_stub": True, "_stub_reason": "Process metrics not integrated - returns placeholder data"},
        }

    def _extract_process_name(self, query: str) -> str:
        """Extract process name from query."""
        words = query.lower().split()
        for word in words:
            if word not in ["improve", "optimize", "analyze", "workflow", "process", "the", "a"]:
                return word.replace("-", "_")
        return "unknown-process"

    async def _analyze_process(
        self, process_name: str, focus: str, query: str
    ) -> dict[str, str]:
        """Analyze a specific process."""
        from agents.research_tools import get_process_metrics

        # Get current metrics (stub)
        metrics = await get_process_metrics(process_name)

        # Build analysis
        analysis = self._build_analysis(process_name, focus, metrics)
        improvement = self._build_improvement_plan(process_name, metrics)
        impact_score = self._calculate_impact(metrics)

        return {
            "analysis": analysis,
            "improvement": improvement,
            "impact_score": impact_score,
        }

    def _build_analysis(
        self, process_name: str, focus: str, metrics: dict
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Process Analysis: {process_name.upper()}",
            f"**Focus**: {focus}",
            f"**Date**: {today}",
            "",
            "## Current State",
            "",
            "### Process Map",
            "```",
            f"[stub] Process map not available - process metrics not integrated",
            "```",
            "",
            "### Metrics",
            f"- **Duration**: {metrics.get('duration', '[stub]')} (target: [stub])",
            f"- **Error Rate**: {metrics.get('error_rate', '[stub]')}% (target: [stub]%)",
            f"- **Steps**: {metrics.get('steps', '[stub]')}",
            f"- **Automation**: {metrics.get('automation', '[stub]')}%",
            "",
            "## Identified Bottlenecks",
            "",
            "### High Impact",
            "- [ ] [stub] Bottleneck 1 not identified",
            "",
            "### Medium Impact",
            "- [ ] [stub] Bottleneck 2 not identified",
            "",
            "### Low Impact",
            "- [ ] [stub] Bottleneck 3 not identified",
            "",
            "## Root Causes",
            "- [stub] Root cause analysis not available",
            "",
            "## Recommendations",
            "- [stub] Specific recommendations not available",
        ]

        lines.append("---")
        lines.append(f"*Generated by Process Optimizer Agent on {today}*")
        return "\n".join(lines)

    def _build_improvement_plan(
        self, process_name: str, metrics: dict
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Improvement Plan: {process_name.upper()}",
            f"**Date**: {today}",
            "",
            "## Goals",
            "",
            "| Metric | Current | Target | Improvement |",
            "|--------|---------|--------|-------------|",
            f"| Duration | {metrics.get('duration', '[stub]')} | [stub] | [stub]% |",
            f"| Error Rate | {metrics.get('error_rate', '[stub]')}% | [stub]% | [stub]% |",
            f"| Automation | {metrics.get('automation', '[stub]')}% | [stub]% | [stub]% |",
            "",
            "## Implementation Phases",
            "",
            "### Phase 1: Quick Wins (Week 1-2)",
            "- [ ] [stub] Quick improvement 1",
            "- [ ] [stub] Quick improvement 2",
            "",
            "### Phase 2: Core Improvements (Week 3-6)",
            "- [ ] [stub] Core improvement 1",
            "- [ ] [stub] Core improvement 2",
            "",
            "### Phase 3: Automation (Week 7-10)",
            "- [ ] [stub] Automation task 1",
            "- [ ] [stub] Automation task 2",
            "",
            "## Success Criteria",
            "- [ ] All Phase 1 tasks completed",
            "- [ ] Duration reduced by 20%",
            "- [ ] Error rate below 5%",
            "- [ ] Automation level above 50%",
        ]
        return "\n".join(lines)

    def _calculate_impact(self, metrics: dict) -> int:
        """Calculate impact score (1-10)."""
        # Stub implementation
        duration = metrics.get("duration", "unknown")
        error_rate = metrics.get("error_rate", 0)
        if isinstance(error_rate, str):
            return 5
        if error_rate > 20:
            return 9
        elif error_rate > 10:
            return 7
        elif error_rate > 5:
            return 5
        return 3

    async def _generate_templates(self, process_name: str) -> dict[str, str]:
        """Generate reusable templates for the process."""
        templates_dir = RESEARCH_DIR / "templates"

        # Generate standard template
        template_content = self._build_template(process_name)
        template_path = templates_dir / f"{process_name}-template.md"
        template_path.write_text(template_content)

        return {"standard_template": str(template_path)}

    def _build_template(self, process_name: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"""# {process_name.title()} Template

**Created**: {today}
**Version**: 1.0

## Steps

### Step 1: TODO
- [ ] Task 1
- [ ] Task 2

### Step 2: TODO
- [ ] Task 1
- [ ] Task 2

## Checklist
- [ ] Pre-conditions met
- [ ] Process completed
- [ ] Post-conditions verified
- [ ] Documentation updated

## Notes
- TODO: Add notes
"""

    async def _generate_automation(
        self, process_name: str, analysis: dict
    ) -> dict[str, str]:
        """Generate automation scripts for the process."""
        tools_dir = RESEARCH_DIR / "tools"

        # Generate automation script stub
        script_content = self._build_automation_script(process_name)
        script_path = tools_dir / f"auto_{process_name}.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        return {"automation_script": str(script_path)}

    def _build_automation_script(self, process_name: str) -> str:
        return f'''#!/bin/bash
# Automation script for {process_name}
# Generated: {datetime.now().strftime("%Y-%m-%d")}

set -e

echo "Running {process_name} automation..."

# TODO: Add automation steps

echo "{process_name} completed."
'''


def create_process_optimizer(llm: Any = None) -> ProcessOptimizerAgent:
    """Factory function to create ProcessOptimizerAgent."""
    return ProcessOptimizerAgent(llm=llm)
