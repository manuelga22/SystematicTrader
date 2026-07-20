# services/rule_registry.py
import inspect


# services/rule_registry.py

ENTRY_RULES: dict[str, callable] = {}
EXIT_RULES: dict[str, callable] = {}

# These functions define decorators that will be used to register the trading rules.

def entry_rule(func):
    """Decorate a function in entries.py to auto-register it."""
    ENTRY_RULES[func.__name__] = func
    return func


def exit_rule(func):
    """Decorate a function in exits.py to auto-register it."""
    EXIT_RULES[func.__name__] = func
    return func


def _collect_rules(module) -> dict[str, callable]:
    return {
        name: func
        for name, func in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_")
    }

