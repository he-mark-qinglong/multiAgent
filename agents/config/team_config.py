"""Team 配置模型"""

from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class TeamMember:
    """Team 成员配置"""
    agent_id: str
    role: str
    prompt_file: Optional[str] = None  # 可选，prompt 文件路径


@dataclass
class TeamConfig:
    """Team 配置"""
    team_id: str
    name: str
    description: str
    members: list[TeamMember] = field(default_factory=list)
    coordination_prompt: Optional[str] = None  # Team 协作 prompt

    @classmethod
    def from_file(cls, file_path: str) -> "TeamConfig":
        """从文件加载配置"""
        from pathlib import Path
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Team config file not found: {file_path}")

        content = path.read_text(encoding="utf-8")

        # 解析 frontmatter
        frontmatter_match = cls._extract_frontmatter(content)
        if frontmatter_match:
            config_dict = yaml.safe_load(frontmatter_match)
        else:
            config_dict = yaml.safe_load(content)

        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config: dict) -> "TeamConfig":
        """从字典加载配置"""
        members = [
            TeamMember(
                agent_id=m.get("agent_id", ""),
                role=m.get("role", "worker"),
                prompt_file=m.get("prompt_file"),
            )
            for m in config.get("members", [])
        ]

        return cls(
            team_id=config.get("team_id", ""),
            name=config.get("name", config.get("team_id", "")),
            description=config.get("description", ""),
            members=members,
            coordination_prompt=config.get("coordination_prompt"),
        )

    @staticmethod
    def _extract_frontmatter(content: str) -> Optional[str]:
        """提取 YAML frontmatter"""
        import re
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        return match.group(1) if match else None

    def get_member(self, agent_id: str) -> Optional[TeamMember]:
        """获取成员"""
        for m in self.members:
            if m.agent_id == agent_id:
                return m
        return None


# 全局缓存
_team_configs: dict[str, TeamConfig] = {}


def load_team_config(file_path: str, use_cache: bool = True) -> TeamConfig:
    """加载 Team 配置"""
    global _team_configs

    if use_cache and file_path in _team_configs:
        return _team_configs[file_path]

    config = TeamConfig.from_file(file_path)
    if use_cache:
        _team_configs[file_path] = config

    return config


def clear_team_config_cache():
    """清空缓存"""
    global _team_configs
    _team_configs.clear()
