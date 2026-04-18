"""Binding configuration schema definitions."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ActionSelector:
    """Single action selector entry."""
    when: Optional[dict] = None
    action: Optional[str] = None
    default: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ActionSelector":
        return cls(
            when=data.get("when"),
            action=data.get("action"),
            default=data.get("default")
        )


@dataclass
class ActionDef:
    """Action definition with params."""
    params: dict = field(default_factory=dict)
    required_params: list = field(default_factory=list)
    idempotent: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ActionDef":
        return cls(
            params=data.get("params", {}),
            required_params=data.get("required_params", []),
            idempotent=data.get("idempotent", False)
        )


@dataclass
class PrimaryConfig:
    """Primary binding configuration."""
    tool: str = ""
    action_selector: list = field(default_factory=list)
    actions: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PrimaryConfig":
        return cls(
            tool=data.get("tool", ""),
            action_selector=[ActionSelector.from_dict(a) for a in data.get("action_selector", [])],
            actions={k: ActionDef.from_dict(v) for k, v in data.get("actions", {}).items()}
        )


@dataclass
class SecondaryConfig:
    """Secondary/fallback binding configuration."""
    description: str = ""
    tool: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SecondaryConfig":
        return cls(
            description=data.get("description", ""),
            tool=data.get("tool", ""),
            action=data.get("action", ""),
            params=data.get("params", {})
        )


@dataclass
class RetryConfig:
    """Retry configuration."""
    enabled: bool = False
    max_attempts: int = 3
    delay_ms: int = 100
    backoff: str = "exponential"
    retry_on: list = field(default_factory=list)
    stop_early_if: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> "RetryConfig":
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            max_attempts=data.get("max_attempts", 3),
            delay_ms=data.get("delay_ms", 100),
            backoff=data.get("backoff", "exponential"),
            retry_on=data.get("retry_on", []),
            stop_early_if=data.get("stop_early_if", [])
        )


@dataclass
class BindingConfig:
    """Complete binding configuration."""
    goal_type: str = ""
    version: str = "v1"
    description: str = ""
    metadata: dict = field(default_factory=dict)
    primary: Optional[PrimaryConfig] = None
    secondary: list = field(default_factory=list)
    retry: RetryConfig = field(default_factory=RetryConfig)
    error_strategy: str = "fallback_then_error"

    @classmethod
    def from_dict(cls, data: dict) -> "BindingConfig":
        primary_data = data.get("primary", {})
        secondary_list = [SecondaryConfig.from_dict(s) for s in data.get("secondary", [])]

        return cls(
            goal_type=data.get("goal_type", ""),
            version=data.get("version", "v1"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            primary=PrimaryConfig.from_dict(primary_data) if primary_data else None,
            secondary=secondary_list,
            retry=RetryConfig.from_dict(data.get("retry", {})),
            error_strategy=data.get("error_strategy", "fallback_then_error")
        )

    @classmethod
    def from_json(cls, json_str: str) -> "BindingConfig":
        import json
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, file_path: str) -> "BindingConfig":
        import json
        with open(file_path) as f:
            return cls.from_dict(json.load(f))
