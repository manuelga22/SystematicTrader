# AGENTS.md

## 1. Project Overview

SYSTEMATICTRADER is a repository that contains 3 mini projects: 
    1. trading_rules, which is a backtesting library written in python.
    2. polymarket_bot, which is a trading bot built for polymarket and also written in python.

 * **Stack**: Python3.11, jupyter notebooks.


## 2. Executable Commands
There is not a single executable or main file at the root level that you can use to run the whole project.

## 3. Architecture & Project Structure
* `trading_rules/`: Backtesting library.
* `polymarket_bot/`: Trading Bot for polymarket.
* `backtests_results/`: folder where I store jupyter notebooks with past market research.
* `data_clients/`: library of clients the provide market data.
* `test/`: unit tests.
* `venv/`: virtual environment for the whole project.
* `util/`: utility folder for common files or functions that don't fit anywhere else.


## 4. Before you start Checklist
***Read the relevant AGENTS.md*** - Each directory has a different purpose and function and rules.

## 5. Ask First:
* Before installing any new third-party npm packages.

## 6. Never Do:
* Never commit or mock hardcoded secrets or API keys.

---

## Mandatory Workflow

** MANDATORY: Always show a plan and get approval before making ANY changes.**

## 1. PLAN

1. **Clarifying questions first** (If ambiguity exists)
   - Use numbered yes/no format when possiblle.
   - Ask about scope and priority.
   - Wait for all answers before proceeding.

2. **Show the  plan** (ALWAYS, no exceptions)
   - List files to be modified/created.
   - Describe the specific changes.
   - Keep it concise but complete.

3. **Ask proceed?** and WAIT for explicit approval

## 2. CODE

- Follow PEP8 conventions.
- Follow all conventions described in the sub-directory `AGENTS.md` files.
- **CRITICAL: Do NOT reformat existing files.** when modifying existing code:
    - **New files**: use PEP8 styling.
    - **existing files:** Match the file's existing style. Only format lines you modified.

## 3. TEST
- Write and run any unit tests if they exist.


## 4. VERIFY
- Self-review against the verification checklist below.
- Confirm no regressions in existing tests.


---

## Python Standards

- Line length: 99 chars
- Quotes: double unless the file is already using single quotes.
- Imports: Absolute only. NO relative imports (`from .`), no wildcards (`from x import *`)


