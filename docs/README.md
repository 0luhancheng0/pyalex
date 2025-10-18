# PyAlex Documentation

This directory contains the documentation for PyAlex, built with MkDocs and Material theme.

## Building Documentation Locally

### Install Dependencies

```bash
pip install -e ".[docs]"
```

### Serve Documentation

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

### Build Static Site

```bash
mkdocs build
```

The built site will be in the `site/` directory.

## Documentation Structure

```
docs/
├── index.md                    # Home page
├── getting-started/            # Installation and setup
│   ├── installation.md
│   ├── quickstart.md
│   └── configuration.md
├── guide/                      # User guides
│   ├── basic-usage.md
│   ├── advanced-filtering.md
│   ├── pagination.md
│   ├── batch-operations.md
│   ├── async-usage.md
│   └── cli-usage.md
├── api/                        # API reference
│   ├── entities/
│   ├── core/
│   ├── client/
│   ├── cli/
│   └── exceptions.md
├── examples/                   # Code examples
│   ├── python.md
│   ├── cli.md
│   └── notebooks.md
├── troubleshooting.md          # Common issues
└── contributing.md             # Contribution guide
```

## Writing Documentation

### Markdown Basics

- Use ATX-style headers (`#`, `##`, etc.)
- Include code blocks with language tags
- Use admonitions for notes/warnings:

```markdown
!!! note "Title"
    Content here
```

### API Documentation

API docs use mkdocstrings to auto-generate from docstrings:

```markdown
::: pyalex.Works
    options:
      show_root_heading: true
      show_source: false
```

### Code Examples

Always include complete, runnable examples:

```python
from pyalex import Works

# Complete example
results = Works().search("AI").get()
for work in results:
    print(work['title'])
```

## Publishing

Documentation is automatically built and published to Read the Docs when changes are pushed to the main branch.

- **Stable**: https://pyalex.readthedocs.io/en/stable/
- **Latest**: https://pyalex.readthedocs.io/en/latest/

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to documentation.
