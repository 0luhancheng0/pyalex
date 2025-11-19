# Repository Guidelines


IF YOU CANT FIND SOME COMMAND IT MAY BE INSTALLED IN THE LOCAL VIRTUAL ENVIRONMENT TRY PREFIX THE COMMAND WITH `pixi run`

## Coding Principles 

- Prioritise simplicity over comprehensiveness
- Try reduce the amount of conditional branching, always prioritise vectorised operations especially when you dealing with pandas dataframe
- If something can be done using existing methods for library, do not rewrite them on your own

Use 4-space indentation, type hints for new public functions, and Google-style docstrings to match existing modules. Modules and functions should stay snake_case, classes PascalCase, and CLI options lowercase with hyphenated names. Keep imports sorted as single lines (enforced by Ruff’s isort settings) and rely on `pyproject.toml` defaults instead of ad-hoc configuration. Prefer Rich-powered logging categories already defined in `pyalex/logger.py` when adding debug output.


NOTE: there are a bunch of standalone script in pyalex/agents directory. Don't need to run test if you are tasked with updating them. 

If you are writing langgraph code, make sure you always reference the full documentation at "/Users/luhancheng/Documents/Obsidian Vault/LLM Context/LangGraph/llms-full.txt"

IF SOMETHING IS WORKING DONT TRY FIXING THEM!!! IF I ASK YOU FIX A SPECIFIC ISSUE, DO NOT TOUCH OTHERS UNLESS I TOLD YOU SO!!!