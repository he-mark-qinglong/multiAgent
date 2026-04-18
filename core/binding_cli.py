"""CLI tools for managing dynamic bindings.

Usage:
    python -m core.binding_cli list
    python -m core.binding_cli show <goal_type>
    python -m core.binding_cli validate [--dir <path>]
    python -m core.binding_cli reload [--dir <path>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from core.binding_schema import BindingConfig


DEFAULT_BINDINGS_DIR = Path("~/.multiagent/bindings").expanduser()


def list_bindings(bindings_dir: Path = DEFAULT_BINDINGS_DIR) -> int:
    """List all bindings in the directory.

    Args:
        bindings_dir: Directory containing binding JSON files

    Returns:
        Exit code (0 for success)
    """
    if not bindings_dir.exists():
        print(f"Bindings directory not found: {bindings_dir}")
        return 1

    files = sorted(bindings_dir.glob("*.json"))
    if not files:
        print(f"No bindings found in {bindings_dir}")
        return 0

    print(f"Bindings in {bindings_dir}:")
    print(f"  {'Goal Type':<25} {'Version':<8} {'Description'}")
    print("  " + "-" * 60)

    for file_path in files:
        goal_type = file_path.stem
        try:
            data = json.loads(file_path.read_text())
            version = data.get("version", "v1")
            description = data.get("description", "")
            print(f"  {goal_type:<25} {version:<8} {description}")
        except Exception as e:
            print(f"  {goal_type:<25} {'ERROR':<8} {e}")

    print(f"\nTotal: {len(files)} bindings")
    return 0


def show_binding(goal_type: str, bindings_dir: Path = DEFAULT_BINDINGS_DIR) -> int:
    """Show detailed info for a specific binding.

    Args:
        goal_type: The goal type to show
        bindings_dir: Directory containing binding JSON files

    Returns:
        Exit code (0 for success)
    """
    file_path = bindings_dir / f"{goal_type}.json"

    if not file_path.exists():
        print(f"Binding not found: {goal_type}")
        print(f"Looking for: {file_path}")
        return 1

    try:
        data = json.loads(file_path.read_text())
        config = BindingConfig.from_dict(data)

        print(f"=== Binding: {config.goal_type} ===")
        print(f"Version: {config.version}")
        print(f"Description: {config.description}")
        print(f"Error Strategy: {config.error_strategy}")
        print()

        if config.primary:
            print(f"Primary Tool: {config.primary.tool}")
            print(f"Action Selectors: {len(config.primary.action_selector)}")
            for i, selector in enumerate(config.primary.action_selector):
                if selector.when:
                    print(f"  [{i+1}] When: {json.dumps(selector.when)}")
                if selector.action:
                    print(f"      -> Action: {selector.action}")
                if selector.default:
                    print(f"      -> Default: {selector.default}")
            print(f"Actions: {list(config.primary.actions.keys())}")
        else:
            print("Primary: None (uses secondary only)")

        if config.secondary:
            print(f"\nSecondary ({len(config.secondary)} fallbacks):")
            for s in config.secondary:
                print(f"  - {s.tool}.{s.action}: {s.description}")

        if config.retry and config.retry.enabled:
            print(f"\nRetry: enabled (max {config.retry.max_attempts} attempts, {config.retry.backoff} backoff)")

        print("\n--- Raw JSON ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        return 0

    except Exception as e:
        print(f"Error loading binding: {e}")
        return 1


def validate_bindings(bindings_dir: Path = DEFAULT_BINDINGS_DIR) -> int:
    """Validate all bindings in the directory.

    Args:
        bindings_dir: Directory containing binding JSON files

    Returns:
        Exit code (0 for all valid, 1 for any error)
    """
    if not bindings_dir.exists():
        print(f"Bindings directory not found: {bindings_dir}")
        return 1

    files = sorted(bindings_dir.glob("*.json"))
    if not files:
        print(f"No bindings found in {bindings_dir}")
        return 0

    errors = []
    valid_count = 0

    for file_path in files:
        goal_type = file_path.stem
        try:
            data = json.loads(file_path.read_text())
            config = BindingConfig.from_dict(data)

            # Validate structure
            if not config.goal_type:
                errors.append(f"{goal_type}: missing goal_type")
            if not config.primary:
                errors.append(f"{goal_type}: missing primary config")

            valid_count += 1
            print(f"  {goal_type}: OK")

        except json.JSONDecodeError as e:
            errors.append(f"{goal_type}: Invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{goal_type}: {e}")

    print(f"\nValidated {valid_count} bindings")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("All bindings are valid!")
    return 0


def reload_bindings(bindings_dir: Path = DEFAULT_BINDINGS_DIR) -> int:
    """Trigger a hot reload of bindings.

    Args:
        bindings_dir: Directory containing binding JSON files

    Returns:
        Exit code (0 for success)
    """
    try:
        from core.binding_manager import get_binding_manager, init_binding_manager
        from core.binding_executor import get_tool_registry

        manager = get_binding_manager()
        results = manager.reload_bindings()

        success = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        print(f"Reloaded {success} bindings successfully")
        if failed:
            print(f"Failed to load {failed} bindings:")
            for goal_type, ok in results.items():
                if not ok:
                    print(f"  - {goal_type}")
            return 1

        return 0

    except ImportError as e:
        print(f"BindingManager not available: {e}")
        return 1
    except Exception as e:
        print(f"Reload failed: {e}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Dynamic Binding Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all bindings")

    # show command
    show_parser = subparsers.add_parser("show", help="Show binding details")
    show_parser.add_argument("goal_type", help="Goal type to show")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate all bindings")
    validate_parser.add_argument("--dir", type=Path, help="Bindings directory")

    # reload command
    reload_parser = subparsers.add_parser("reload", help="Hot reload bindings")
    reload_parser.add_argument("--dir", type=Path, help="Bindings directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    bindings_dir = args.dir if hasattr(args, "dir") and args.dir else DEFAULT_BINDINGS_DIR

    if args.command == "list":
        return list_bindings(bindings_dir)
    elif args.command == "show":
        return show_binding(args.goal_type, bindings_dir)
    elif args.command == "validate":
        return validate_bindings(bindings_dir)
    elif args.command == "reload":
        return reload_bindings(bindings_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
