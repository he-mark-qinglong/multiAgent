"""Prompt Loader - 从文件加载 prompt，支持变量替换"""

import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class LoadOptions:
    """Prompt 加载选项"""
    base_dir: Optional[Path] = None  # 如果 prompt 引用相对路径从这里解析
    variables: Optional[dict] = None  # 额外的变量替换
    encoding: str = "utf-8"


class PromptLoader:
    """Prompt 加载器，支持 $VAR 和 ${VAR} 变量替换"""

    VAR_PATTERN = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?')
    FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)

    def __init__(self, base_dir: Optional[Path] = None):
        # base_dir 是项目根目录，不是 prompts 目录
        self.base_dir = base_dir or Path(__file__).parent.parent.parent

    def load(
        self,
        source: str,
        variables: Optional[dict] = None,
        base_dir: Optional[Path] = None,
    ) -> str:
        """
        加载 prompt 内容

        Args:
            source: prompt 文件路径或直接的内容
            variables: 变量替换字典
            base_dir: 相对路径解析的基准目录

        Returns:
            加载并处理后的 prompt 内容
        """
        # 如果是文件路径，加载文件内容
        if self._is_file_path(source):
            content = self._load_file(source, base_dir)
        else:
            content = source

        # 合并变量
        vars_dict = variables or {}

        # 执行变量替换
        content = self._substitute_variables(content, vars_dict)

        return content

    def _is_file_path(self, source: str) -> bool:
        """判断是否是文件路径"""
        # 相对路径或绝对路径
        if os.path.sep in source or source.startswith("."):
            return True
        # 常见的 prompt 目录
        if any(source.startswith(d) for d in ["prompts/", "system/", "context/", "tools/"]):
            return True
        return False

    def _load_file(self, file_path: str, base_dir: Optional[Path] = None) -> str:
        """从文件加载内容"""
        # 确定基准目录
        base = base_dir or self.base_dir

        # 如果已经是绝对路径
        if file_path.startswith(os.path.sep):
            full_path = Path(file_path)
        else:
            # 相对路径从 base 开始
            full_path = base / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {full_path}")

        return full_path.read_text(encoding="utf-8")

    def _substitute_variables(self, content: str, variables: dict) -> str:
        """执行变量替换"""
        def replacer(match):
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            # 如果没有对应变量，保留原样
            return match.group(0)

        return self.VAR_PATTERN.sub(replacer, content)

    def load_with_frontmatter(
        self,
        source: str,
        variables: Optional[dict] = None,
        base_dir: Optional[Path] = None,
    ) -> tuple[Optional[dict], str]:
        """
        加载包含 YAML frontmatter 的 prompt

        Returns:
            (frontmatter_dict, prompt_content) 元组
        """
        content = self.load(source, variables, base_dir)

        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            import yaml
            frontmatter = yaml.safe_load(match.group(1))
            body = content[match.end():]
            return frontmatter, body

        return None, content

    def resolve_relative_path(self, source: str, relative_to: str) -> str:
        """解析相对路径"""
        base = Path(relative_to).parent
        full_path = (base / source).resolve()
        return str(full_path)


# 全局单例
_default_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """获取全局 PromptLoader 实例"""
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader


def load_prompt(
    source: str,
    variables: Optional[dict] = None,
    base_dir: Optional[Path] = None,
) -> str:
    """快捷函数：加载 prompt"""
    return get_prompt_loader().load(source, variables, base_dir)


def load_prompt_with_frontmatter(
    source: str,
    variables: Optional[dict] = None,
    base_dir: Optional[Path] = None,
) -> tuple[Optional[dict], str]:
    """快捷函数：加载带 frontmatter 的 prompt"""
    return get_prompt_loader().load_with_frontmatter(source, variables, base_dir)
