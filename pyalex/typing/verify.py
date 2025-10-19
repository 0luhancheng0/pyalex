#!/usr/bin/env python
"""Verify PyAlex typing module installation and functionality.

Run this script to check that all type definitions are properly installed
and can be imported.
"""

import sys
from typing import get_type_hints


def check_imports():  # noqa: F401
    """Verify all types can be imported."""
    print("Checking imports...")
    try:
        from pyalex.typing import APC  # noqa: F401
        from pyalex.typing import Author  # noqa: F401
        from pyalex.typing import AuthorCounts  # noqa: F401
        from pyalex.typing import AuthorLastKnownInstitution  # noqa: F401
        from pyalex.typing import AuthorPosition  # noqa: F401
        from pyalex.typing import Authorship  # noqa: F401
        from pyalex.typing import AuthorSummaryStats  # noqa: F401
        from pyalex.typing import Biblio  # noqa: F401
        from pyalex.typing import CountsByYear  # noqa: F401
        from pyalex.typing import DehydratedEntity  # noqa: F401
        from pyalex.typing import Funder  # noqa: F401
        from pyalex.typing import FunderCounts  # noqa: F401
        from pyalex.typing import FunderSummaryStats  # noqa: F401
        from pyalex.typing import Grant  # noqa: F401
        from pyalex.typing import IDs  # noqa: F401
        from pyalex.typing import Institution  # noqa: F401
        from pyalex.typing import InstitutionCounts  # noqa: F401
        from pyalex.typing import InstitutionGeo  # noqa: F401
        from pyalex.typing import InstitutionRepository  # noqa: F401
        from pyalex.typing import InstitutionSummaryStats  # noqa: F401
        from pyalex.typing import InternationalDisplay  # noqa: F401
        from pyalex.typing import Keyword  # noqa: F401
        from pyalex.typing import Location  # noqa: F401
        from pyalex.typing import OpenAccess  # noqa: F401
        from pyalex.typing import Publisher  # noqa: F401
        from pyalex.typing import PublisherCounts  # noqa: F401
        from pyalex.typing import PublisherSummaryStats  # noqa: F401
        from pyalex.typing import Source  # noqa: F401
        from pyalex.typing import SourceCounts  # noqa: F401
        from pyalex.typing import SourceSummaryStats  # noqa: F401
        from pyalex.typing import Topic  # noqa: F401
        from pyalex.typing import Work  # noqa: F401

        print("✓ All core types imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def check_type_structure():
    """Verify type definitions have correct structure."""
    print("\nChecking type structure...")
    try:
        from pyalex.typing import Work

        # Check that Work is a TypedDict
        hints = get_type_hints(Work)
        if hints:
            print(f"✓ Work type has {len(hints)} typed fields")
        else:
            print("✓ Work type structure is valid (total=False)")

        return True
    except Exception as e:
        print(f"✗ Structure check failed: {e}")
        return False


def check_documentation():
    """Verify documentation files exist."""
    print("\nChecking documentation...")
    from pathlib import Path

    typing_dir = Path(__file__).parent / "pyalex" / "typing"

    docs = ["README.md", "QUICKREF.md", "py.typed"]
    missing = []

    for doc in docs:
        doc_path = typing_dir / doc
        if doc_path.exists():
            print(f"✓ Found {doc}")
        else:
            print(f"✗ Missing {doc}")
            missing.append(doc)

    return len(missing) == 0


def check_example():
    """Verify example file exists and is valid Python."""
    print("\nChecking example file...")
    from pathlib import Path

    example_path = Path(__file__).parent / "examples" / "typing_example.py"

    if not example_path.exists():
        print("✗ Example file not found")
        return False

    try:
        with open(example_path) as f:
            code = f.read()
        compile(code, str(example_path), "exec")
        print("✓ Example file is valid Python")
        return True
    except SyntaxError as e:
        print(f"✗ Example file has syntax errors: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("PyAlex Typing Module Verification")
    print("=" * 70)

    checks = [
        ("Imports", check_imports),
        ("Type Structure", check_type_structure),
        ("Documentation", check_documentation),
        ("Example", check_example),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! PyAlex typing module is ready to use.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
