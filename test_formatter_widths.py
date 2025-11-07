"""Test that all formatters use consistent max_width."""

from pyalex.cli.formatters import AuthorsTableFormatter
from pyalex.cli.formatters import InstitutionsTableFormatter
from pyalex.cli.formatters import PublishersTableFormatter
from pyalex.cli.formatters import SourcesTableFormatter
from pyalex.cli.formatters import WorksTableFormatter

# Create formatters
formatters = {
    "Works": WorksTableFormatter(),
    "Authors": AuthorsTableFormatter(),
    "Institutions": InstitutionsTableFormatter(),
    "Sources": SourcesTableFormatter(),
    "Publishers": PublishersTableFormatter(),
}

print("Formatter Max Width Consistency Test")
print("=" * 60)

# Check that all formatters have the same max_width
for name, formatter in formatters.items():
    print(f"{name:15} max_width: {formatter.max_width}")

# Test with sample data
print("\n" + "=" * 60)
print("Testing name field truncation with long names")
print("=" * 60)

long_name = (
    "A Very Long Name That Tests The Maximum Width "
    "Configuration And Shows How Tables Will Display "
    "Long Entity Names Without Arbitrary Truncation "
    "To Short Lengths Like 40 Characters"
)

# Test each formatter
source_data = {
    "display_name": long_name,
    "type": "journal",
    "issn_l": "1234-5678",
    "works_count": 50000,
    "id": "https://openalex.org/S12345",
}

work_data = {
    "title": long_name,
    "publication_year": 2024,
    "primary_location": {"source": {"display_name": "Nature"}},
    "cited_by_count": 100,
    "id": "https://openalex.org/W67890",
}

author_data = {
    "display_name": long_name,
    "works_count": 100,
    "cited_by_count": 5000,
    "last_known_institution": {"display_name": "MIT"},
    "id": "https://openalex.org/A12345",
}

institution_data = {
    "display_name": long_name,
    "country_code": "US",
    "works_count": 100000,
    "cited_by_count": 1000000,
    "id": "https://openalex.org/I12345",
}

publisher_data = {
    "display_name": long_name,
    "hierarchy_level": 0,
    "works_count": 50000,
    "sources_count": 100,
    "id": "https://openalex.org/P12345",
}

results = {
    "Sources": formatters["Sources"].extract_row_data(source_data)[0],
    "Works": formatters["Works"].extract_row_data(work_data)[0],
    "Authors": formatters["Authors"].extract_row_data(author_data)[0],
    "Institutions": formatters["Institutions"].extract_row_data(institution_data)[0],
    "Publishers": formatters["Publishers"].extract_row_data(publisher_data)[0],
}

print(f"\nOriginal name length: {len(long_name)} characters")
print()
for entity_type, truncated_name in results.items():
    print(f"{entity_type:15} name length: {len(truncated_name):3} characters")

# Check consistency
lengths = [len(name) for name in results.values()]
if len(set(lengths)) == 1:
    print("\n✅ All formatters truncate names consistently!")
else:
    print("\n⚠️  Formatters have different truncation lengths")
    print(f"   Unique lengths: {set(lengths)}")
