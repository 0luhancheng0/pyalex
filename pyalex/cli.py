#!/usr/bin/env python3
"""
PyAlex CLI - Command line interface for the OpenAlex database
"""
import datetime
import json
import os
import sys
import traceback
from typing import Optional

import typer
from prettytable import PrettyTable
from typing_extensions import Annotated

from pyalex import Authors
from pyalex import Domains
from pyalex import Fields
from pyalex import Funders
from pyalex import Institutions
from pyalex import Keywords
from pyalex import Publishers
from pyalex import Sources
from pyalex import Subfields
from pyalex import Topics
from pyalex import Works
from pyalex import config
from pyalex import invert_abstract


# Global verbose state
_verbose_mode = False

MAX_WIDTH = 100

app = typer.Typer(
    name="pyalex",
    help="CLI interface for the OpenAlex database",
    no_args_is_help=True,
)

# Global options


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output including API URLs for debugging"
    )] = False,
):
    """
    PyAlex CLI - Access the OpenAlex database from the command line.
    
    OpenAlex doesn't require authentication for most requests.
    """
    global _verbose_mode
    _verbose_mode = verbose
    
    if verbose:
        typer.echo(f"Email: {config.email}")
        typer.echo(f"User Agent: {config.user_agent}")
        typer.echo("Verbose mode enabled - API URLs will be displayed")


def _print_debug_url(query):
    """Print the constructed URL for debugging when verbose mode is enabled."""
    if _verbose_mode:
        typer.echo(f"[DEBUG] API URL: {query.url}", err=True)


def _print_debug_results(results):
    """Print debug information about results when verbose mode is enabled."""
    if _verbose_mode and results is not None:
        typer.echo(f"[DEBUG] Results type: {type(results)}", err=True)
        if hasattr(results, '__len__'):
            typer.echo(f"[DEBUG] Results length: {len(results)}", err=True)
        if hasattr(results, 'meta') and results.meta:
            count = results.meta.get('count')
            if count is not None:
                typer.echo(f"[DEBUG] Total count from meta: {count}", err=True)


def _add_abstract_to_work(work_dict):
    """Convert inverted abstract index to readable abstract for a work."""
    if (isinstance(work_dict, dict) and 
        'abstract_inverted_index' in work_dict and 
        work_dict['abstract_inverted_index'] is not None):
        work_dict['abstract'] = invert_abstract(work_dict['abstract_inverted_index'])
    return work_dict


@app.command()
def works(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for works"
    )] = None,
    author_id: Annotated[Optional[str], typer.Option(
        "--author-id",
        help="Filter by author OpenAlex ID"
    )] = None,
    institution_id: Annotated[Optional[str], typer.Option(
        "--institution-id", 
        help="Filter by institution OpenAlex ID"
    )] = None,
    publication_year: Annotated[Optional[str], typer.Option(
        "--year",
        help="Filter by publication year (e.g. '2020' or range '2019:2021')"
    )] = None,
    publication_date: Annotated[Optional[str], typer.Option(
        "--date",
        help="Filter by publication date (e.g. '2020-01-01' or "
             "range '2019-01-01:2020-12-31')"
    )] = None,
    work_type: Annotated[Optional[str], typer.Option(
        "--type",
        help="Filter by work type (e.g. 'article', 'book', 'dataset')"
    )] = None,
    topic_id: Annotated[Optional[str], typer.Option(
        "--topic-id",
        help="Filter by primary topic OpenAlex ID"
    )] = None,
    subfield_id: Annotated[Optional[str], typer.Option(
        "--subfield-id",
        help="Filter by primary topic subfield OpenAlex ID"
    )] = None,
    funder_id: Annotated[Optional[str], typer.Option(
        "--funder-id",
        help="Filter by funder OpenAlex ID"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'oa_status', 'publication_year', "
             "'type', 'is_retracted', 'cited_by_count')"
    )] = None,
    include_abstract: Annotated[bool, typer.Option(
        "--abstract",
        help="Include full abstracts in output (when available)"
    )] = True,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, title, table, summary"
    )] = "table",
    work_id: Annotated[Optional[str], typer.Argument(
        help="Specific work ID to retrieve"
    )] = None,
):
    """
    Search and retrieve works from OpenAlex.
    
    Examples:
      pyalex works --search "machine learning"
      pyalex works --author-id "A1234567890" --limit 5
      pyalex works --year "2019:2020" --limit 10
      pyalex works --date "2020-01-01:2020-12-31" --limit 10
      pyalex works --date "2020-06-15" --limit 5
      pyalex works --type "article" --search "COVID-19"
      pyalex works --topic-id "T10002" --limit 5
      pyalex works --subfield-id "SF12345" --limit 5
      pyalex works --funder-id "F4320332161" --limit 5
      pyalex works --search "AI" --abstract --format summary
      pyalex works --group-by "oa_status" --format table
      pyalex works --group-by "publication_year" --search "COVID-19"
      pyalex works W1234567890
    """
    try:
        if work_id:
            # Get specific work
            work = Works()[work_id]
            if _verbose_mode:
                typer.echo(f"[DEBUG] API URL: {Works().url}/{work_id}", err=True)
            # Convert abstract for single work if requested
            if include_abstract:
                work = _add_abstract_to_work(work)
            _output_results(work, output_format, single=True)
        else:
            # Search works
            query = Works()
            
            if search:
                query = query.search(search)
            if author_id:
                query = query.filter(author={"id": author_id})
            if institution_id:
                query = query.filter(
                    authorships={"institutions": {"id": institution_id}}
                )
            if publication_year:
                # Handle publication year ranges (e.g., "2019:2020") or single years
                if ":" in publication_year:
                    try:
                        start_year, end_year = publication_year.split(":")
                        start_year = int(start_year.strip())
                        end_year = int(end_year.strip())
                        
                        # For inclusive range, use >= start_year and <= end_year
                        # Since PyAlex only supports > and <, we'll use 
                        # (start_year - 1) and (end_year + 1)
                        query = query.filter_gt(publication_year=start_year - 1)
                        query = query.filter_lt(publication_year=end_year + 1)
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year range format. Use 'start:end' "
                            "(e.g., '2019:2020')", 
                            err=True
                        )
                        raise typer.Exit(1) from None
                else:
                    try:
                        year = int(publication_year.strip())
                        query = query.filter(publication_year=year)
                    except ValueError:
                        typer.echo(
                            "Error: Invalid year format. Use a single year or range "
                            "(e.g., '2020' or '2019:2020')", 
                            err=True
                        )
                        raise typer.Exit(1) from None
            
            if publication_date:
                # Handle publication date ranges (e.g., "2019-01-01:2020-12-31") 
                # or single dates
                if ":" in publication_date:
                    try:
                        start_date, end_date = publication_date.split(":")
                        start_date = start_date.strip()
                        end_date = end_date.strip()
                        
                        # Validate date format (basic check for YYYY-MM-DD)
                        datetime.datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.datetime.strptime(end_date, "%Y-%m-%d")
                        
                        # For inclusive range, we need >= start_date and <= end_date
                        # We'll use from_publication_date and to_publication_date
                        query = query.filter(from_publication_date=start_date)
                        query = query.filter(to_publication_date=end_date)
                    except ValueError as ve:
                        typer.echo(
                            "Error: Invalid date range format. Use "
                            "'YYYY-MM-DD:YYYY-MM-DD' (e.g., '2019-01-01:2020-12-31')", 
                            err=True
                        )
                        raise typer.Exit(1) from ve
                else:
                    try:
                        # Validate single date format
                        datetime.datetime.strptime(publication_date.strip(), "%Y-%m-%d")
                        query = query.filter(publication_date=publication_date.strip())
                    except ValueError:
                        typer.echo(
                            "Error: Invalid date format. Use YYYY-MM-DD format "
                            "(e.g., '2020-01-01') or range '2019-01-01:2020-12-31'", 
                            err=True
                        )
                        raise typer.Exit(1) from None
            
            if work_type:
                query = query.filter(type=work_type)
            
            if topic_id:
                query = query.filter(primary_topic={"id": topic_id})
            
            if subfield_id:
                query = query.filter(primary_topic={"subfield": {"id": subfield_id}})
            
            if funder_id:
                query = query.filter(grants={"funder": funder_id})

            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                try:
                    # For group-by operations, retrieve all groups by default
                    results = query.get(limit=100000)  # High limit to get all groups
                    _print_debug_results(results)
                except Exception as api_error:
                    typer.echo(f"[DEBUG] API call failed: {api_error}", err=True)
                    raise
                
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            
            try:
                results = query.get(limit=limit)
                _print_debug_results(results)
            except Exception as api_error:
                typer.echo(f"[DEBUG] API call failed: {api_error}", err=True)
                raise
            
            # Check if results is None or empty
            if results is None:
                typer.echo("No results returned from API", err=True)
                return
            
            # Convert abstracts for all works in results if requested
            if results and include_abstract:
                results = [_add_abstract_to_work(work) for work in results]
                
            _output_results(results, output_format)
            
    except Exception as e:
        if _verbose_mode:
            import traceback
            typer.echo("[DEBUG] Full traceback:", err=True)
            traceback.print_exc()
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def from_ids(
    include_abstract: Annotated[bool, typer.Option(
        "--abstract",
        help="Include full abstracts in output for works (when available)"
    )] = False,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name/title, table, summary"
    )] = "table",
):
    """
    Retrieve multiple entities by their OpenAlex IDs from stdin.
    
    This command automatically detects the entity type from the ID prefix and retrieves
    the appropriate entities. It can handle mixed entity types in the same input.
    
    Supported ID prefixes:
    - W: Works
    - A: Authors  
    - I: Institutions
    - S: Sources (journals/venues)
    - T: Topics
    - P: Publishers
    - F: Funders
    - D: Domains
    - SF: Subfields
    
    Examples:
      echo '["W1234", "A5678", "I9012"]' | pyalex from-ids --format json
      echo -e "A1234567890\\nW9876543210" | pyalex from-ids --format table
      echo '["W1234"]' | pyalex from-ids --abstract --format summary
    """
    try:
        # Read from stdin
        stdin_content = sys.stdin.read().strip()
        
        if not stdin_content:
            typer.echo("Error: No input provided via stdin", err=True)
            raise typer.Exit(1)
        
        # Try to parse as JSON array first
        entity_ids = []
        try:
            parsed = json.loads(stdin_content)
            if isinstance(parsed, list):
                entity_ids = parsed
            else:
                typer.echo(
                    "Error: JSON input must be an array of entity IDs",
                    err=True
                )
                raise typer.Exit(1)
        except json.JSONDecodeError:
            # If not valid JSON, treat as newline-separated IDs
            entity_ids = [
                line.strip() 
                for line in stdin_content.split('\n') 
                if line.strip()
            ]
        
        if not entity_ids:
            typer.echo("Error: No entity IDs found in input", err=True)
            raise typer.Exit(1)
        
        # Clean up all entity IDs (remove URL prefix if present)
        cleaned_entity_ids = []
        for entity_id in entity_ids:
            if isinstance(entity_id, str):
                # Remove URL prefix if present
                clean_id = entity_id.replace('https://openalex.org/', '').strip()
                # Also handle cases where there might be extra slashes or whitespace
                clean_id = clean_id.strip('/')
                # Remove quotes that might be added by jq or other tools
                clean_id = clean_id.strip('"\'')
                if clean_id:  # Only add non-empty IDs
                    cleaned_entity_ids.append(clean_id)
        
        if not cleaned_entity_ids:
            typer.echo(
                "Error: No valid entity IDs found after cleaning input",
                err=True
            )
            raise typer.Exit(1)
        
        if _verbose_mode:
            typer.echo(
                f"[DEBUG] Processing {len(cleaned_entity_ids)} entity IDs",
                err=True
            )
            typer.echo(f"[DEBUG] First few IDs: {cleaned_entity_ids[:3]}", err=True)
        
        # Group IDs by entity type
        entity_groups = {}
        for entity_id in cleaned_entity_ids:
            entity_class, entity_name, entity_plural = _detect_entity_type(entity_id)
            
            if entity_class not in entity_groups:
                entity_groups[entity_class] = {
                    'ids': [],
                    'name': entity_name,
                    'plural': entity_plural
                }
            entity_groups[entity_class]['ids'].append(entity_id)
        
        if _verbose_mode:
            for _entity_class, group in entity_groups.items():
                typer.echo(
                    f"[DEBUG] Found {len(group['ids'])} {group['plural']}: "
                    f"{group['ids'][:3]}{'...' if len(group['ids']) > 3 else ''}",
                    err=True
                )
        
        # Retrieve entities for each type
        all_entities = []
        for entity_class, group in entity_groups.items():
            entity_name = group['name']
            entity_plural = group['plural']
            entity_ids_for_type = group['ids']
            
            # Determine special processing based on entity type
            special_processing = None
            if entity_class == Works and include_abstract:
                special_processing = _add_abstract_to_work
            
            # Retrieve entities in batches of up to 50 (OpenAlex limit for OR filters)
            batch_size = 50
            
            for i in range(0, len(entity_ids_for_type), batch_size):
                batch_ids = entity_ids_for_type[i:i + batch_size]
                
                if _verbose_mode:
                    typer.echo(
                        f"[DEBUG] Fetching {entity_plural} batch "
                        f"{i//batch_size + 1}: {len(batch_ids)} entities", 
                        err=True
                    )
                
                try:
                    # Create OR filter for batch of entity IDs
                    # Format: "A123|A456|A789"
                    id_filter = "|".join(batch_ids)
                    
                    # Query entities using OR filter
                    # Keywords use 'id' field instead of 'openalex_id'
                    if entity_class == Keywords:
                        query = entity_class().filter(id=id_filter)
                    else:
                        query = entity_class().filter(openalex_id=id_filter)
                    
                    if _verbose_mode:
                        typer.echo(f"[DEBUG] API URL: {query.url}", err=True)
                    
                    # Get all results for this batch (no limit since we want all 
                    # requested entities)
                    batch_results = query.get()
                    
                    if batch_results:
                        # Apply special processing if provided
                        if special_processing:
                            batch_results = [
                                special_processing(entity) for entity in batch_results
                            ]
                        
                        all_entities.extend(batch_results)
                        
                        if _verbose_mode:
                            typer.echo(
                                f"[DEBUG] Successfully retrieved {len(batch_results)} "
                                f"{entity_plural} from batch", 
                                err=True
                            )
                    else:
                        if _verbose_mode:
                            typer.echo(
                                f"[DEBUG] No {entity_plural} returned for batch", 
                                err=True
                            )
                    
                except Exception as e:
                    if _verbose_mode:
                        typer.echo(
                            f"[DEBUG] Failed to fetch batch: {e}", 
                            err=True
                        )
                        # Fall back to individual requests for this batch
                        typer.echo(
                            "[DEBUG] Falling back to individual requests for batch", 
                            err=True
                        )
                        
                        for clean_id in batch_ids:
                            try:
                                entity = entity_class()[clean_id]
                                if special_processing:
                                    entity = special_processing(entity)
                                all_entities.append(entity)
                            except Exception as individual_error:
                                typer.echo(
                                    f"Warning: Could not retrieve {entity_name} "
                                    f"{clean_id}: {individual_error}", 
                                    err=True
                                )
                                continue
                    else:
                        typer.echo(
                            f"Warning: Could not retrieve batch of {len(batch_ids)} "
                            f"{entity_plural}: {e}", 
                            err=True
                        )
                    continue
        
        if not all_entities:
            typer.echo("Error: No entities could be retrieved", err=True)
            raise typer.Exit(1)
        
        if _verbose_mode:
            typer.echo(
                f"[DEBUG] Successfully retrieved {len(all_entities)} total entities",
                err=True
            )
        
        _output_results(all_entities, output_format)
        
    except Exception as e:
        if _verbose_mode:
            typer.echo("[DEBUG] Full traceback:", err=True)
            traceback.print_exc()
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


def _detect_entity_type(entity_id):
    """
    Detect the entity type from an OpenAlex ID prefix.
    
    Returns:
        tuple: (entity_class, entity_name, entity_plural)
        
    Raises:
        ValueError: If entity ID format is not recognized
    """
    # Mapping of ID prefixes to entity classes and names
    prefix_mapping = {
        'W': (Works, "work", "works"),
        'A': (Authors, "author", "authors"),
        'I': (Institutions, "institution", "institutions"),
        'S': (Sources, "source", "sources"),
        'T': (Topics, "topic", "topics"),
        'P': (Publishers, "publisher", "publishers"),
        'F': (Funders, "funder", "funders"),
        'D': (Domains, "domain", "domains"),
        'SF': (Subfields, "subfield", "subfields"),
    }
    
    # Check for subfield first (SF prefix)
    if entity_id.startswith('SF') and len(entity_id) > 2 and entity_id[2:].isdigit():
        return prefix_mapping['SF']
    
    # Check single letter prefixes - only if ID looks like standard OpenAlex format
    # Standard format: letter followed by numbers (e.g., W123456789, A5083138872)
    if len(entity_id) > 1 and entity_id[0].upper() in prefix_mapping:
        # Verify it follows the pattern: letter + digits
        if entity_id[1:].isdigit():
            prefix = entity_id[0].upper()
            return prefix_mapping[prefix]
    
    # Raise error for unrecognized formats
    raise ValueError(f"Unrecognized entity ID format: {entity_id}. "
                    f"Supported prefixes: {', '.join(prefix_mapping.keys())}")


def _entities_from_ids(
    entity_class, entity_name, entity_plural, special_processing=None
):
    """
    Generic function to retrieve multiple entities by their OpenAlex IDs from stdin.
    
    Args:
        entity_class: The PyAlex class (e.g., Authors, Works, etc.)
        entity_name: Singular name for display (e.g., "author", "work")
        entity_plural: Plural name for display (e.g., "authors", "works")
        special_processing: Optional function to apply special processing to each entity
    """
    
    try:
        # Read from stdin
        stdin_content = sys.stdin.read().strip()
        
        if not stdin_content:
            typer.echo("Error: No input provided via stdin", err=True)
            raise typer.Exit(1)
        
        # Try to parse as JSON array first
        entity_ids = []
        try:
            parsed = json.loads(stdin_content)
            if isinstance(parsed, list):
                entity_ids = parsed
            else:
                typer.echo(
                    f"Error: JSON input must be an array of {entity_name} IDs",
                    err=True
                )
                raise typer.Exit(1)
        except json.JSONDecodeError:
            # If not valid JSON, treat as newline-separated IDs
            entity_ids = [
                line.strip() 
                for line in stdin_content.split('\n') 
                if line.strip()
            ]
        
        if not entity_ids:
            typer.echo(f"Error: No {entity_name} IDs found in input", err=True)
            raise typer.Exit(1)
        
        # Clean up all entity IDs (remove URL prefix if present)
        cleaned_entity_ids = []
        for entity_id in entity_ids:
            if isinstance(entity_id, str):
                # Remove URL prefix if present
                clean_id = entity_id.replace('https://openalex.org/', '').strip()
                # Also handle cases where there might be extra slashes or whitespace
                clean_id = clean_id.strip('/')
                # Remove quotes that might be added by jq or other tools
                clean_id = clean_id.strip('"\'')
                if clean_id:  # Only add non-empty IDs
                    cleaned_entity_ids.append(clean_id)
        
        if not cleaned_entity_ids:
            typer.echo(
                f"Error: No valid {entity_name} IDs found after cleaning input",
                err=True
            )
            raise typer.Exit(1)
        
        if _verbose_mode:
            typer.echo(
                f"[DEBUG] Processing {len(cleaned_entity_ids)} {entity_name} IDs",
                err=True
            )
            typer.echo(f"[DEBUG] First few IDs: {cleaned_entity_ids[:3]}", err=True)
        
        # Retrieve entities in batches of up to 50 (OpenAlex limit for OR filters)
        entities = []
        batch_size = 50
        
        for i in range(0, len(cleaned_entity_ids), batch_size):
            batch_ids = cleaned_entity_ids[i:i + batch_size]
            
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] Fetching batch {i//batch_size + 1}: "
                    f"{len(batch_ids)} {entity_plural}", 
                    err=True
                )
            
            try:
                # Create OR filter for batch of entity IDs
                # Format: "A123|A456|A789"
                id_filter = "|".join(batch_ids)
                
                # Query entities using OR filter
                # Keywords use 'id' field instead of 'openalex_id'
                if entity_class == Keywords:
                    query = entity_class().filter(id=id_filter)
                else:
                    query = entity_class().filter(openalex_id=id_filter)
                
                if _verbose_mode:
                    typer.echo(f"[DEBUG] API URL: {query.url}", err=True)
                
                # Get all results for this batch (no limit since we want all 
                # requested entities)
                batch_results = query.get()
                
                if batch_results:
                    # Apply special processing if provided
                    if special_processing:
                        batch_results = [
                            special_processing(entity) for entity in batch_results
                        ]
                    
                    entities.extend(batch_results)
                    
                    if _verbose_mode:
                        typer.echo(
                            f"[DEBUG] Successfully retrieved {len(batch_results)} "
                            f"{entity_plural} from batch", 
                            err=True
                        )
                else:
                    if _verbose_mode:
                        typer.echo(
                            f"[DEBUG] No {entity_plural} returned for batch", 
                            err=True
                        )
                
            except Exception as e:
                if _verbose_mode:
                    typer.echo(
                        f"[DEBUG] Failed to fetch batch: {e}", 
                        err=True
                    )
                    # Fall back to individual requests for this batch
                    typer.echo(
                        "[DEBUG] Falling back to individual requests for batch", 
                        err=True
                    )
                    
                    for clean_id in batch_ids:
                        try:
                            entity = entity_class()[clean_id]
                            if special_processing:
                                entity = special_processing(entity)
                            entities.append(entity)
                        except Exception as individual_error:
                            typer.echo(
                                f"Warning: Could not retrieve {entity_name} "
                                f"{clean_id}: {individual_error}", 
                                err=True
                            )
                            continue
                else:
                    typer.echo(
                        f"Warning: Could not retrieve batch of {len(batch_ids)} "
                        f"{entity_plural}: {e}", 
                        err=True
                    )
                continue
        
        if not entities:
            typer.echo(f"Error: No {entity_plural} could be retrieved", err=True)
            raise typer.Exit(1)
        
        if _verbose_mode:
            typer.echo(
                f"[DEBUG] Successfully retrieved {len(entities)} {entity_plural}",
                err=True
            )
        
        return entities
        
    except Exception as e:
        if _verbose_mode:
            typer.echo("[DEBUG] Full traceback:", err=True)
            traceback.print_exc()
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def authors(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for authors"
    )] = None,
    institution_id: Annotated[Optional[str], typer.Option(
        "--institution-id",
        help="Filter by institution OpenAlex ID"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'cited_by_count', 'has_orcid', "
             "'works_count')"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    author_id: Annotated[Optional[str], typer.Argument(
        help="Specific author ID to retrieve"
    )] = None,
):
    """
    Search and retrieve authors from OpenAlex.
    
    Examples:
      pyalex authors --search "John Smith"
      pyalex authors --institution-id "I1234567890" --limit 5
      pyalex authors --group-by "cited_by_count" --format summary
      pyalex authors --group-by "has_orcid" --format table
      pyalex authors A1234567890
    """
    try:
        if author_id:
            # Get specific author
            author = Authors()[author_id]
            if _verbose_mode:
                typer.echo(f"[DEBUG] API URL: {Authors().url}/{author_id}", err=True)
            _output_results(author, output_format, single=True)
        else:
            # Search authors
            query = Authors()
            
            if search:
                query = query.search(search)
            if institution_id:
                query = query.filter(last_known_institutions={"id": institution_id})
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                try:
                    # For group-by operations, retrieve all groups by default
                    results = query.get(limit=100000)  # High limit to get all groups
                    if _verbose_mode:
                        typer.echo(f"[DEBUG] Results type: {type(results)}", err=True)
                        if hasattr(results, '__len__'):
                            typer.echo(
                                f"[DEBUG] Results length: {len(results)}", 
                                err=True
                            )
                except Exception as api_error:
                    typer.echo(f"[DEBUG] API call failed: {api_error}", err=True)
                    raise
                
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def topics(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for topics"
    )] = None,
    domain_id: Annotated[Optional[str], typer.Option(
        "--domain-id",
        help="Filter by domain OpenAlex ID"
    )] = None,
    field_id: Annotated[Optional[str], typer.Option(
        "--field-id",
        help="Filter by field OpenAlex ID" 
    )] = None,
    subfield_id: Annotated[Optional[str], typer.Option(
        "--subfield-id",
        help="Filter by subfield OpenAlex ID"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    topic_id: Annotated[Optional[str], typer.Argument(
        help="Specific topic ID to retrieve"
    )] = None,
):
    """
    Search and retrieve topics from OpenAlex.
    
    Examples:
      pyalex topics --search "artificial intelligence"
      pyalex topics --domain-id "D1234567890" --limit 5
      pyalex topics --field-id "F1234567890" --limit 5
      pyalex topics --subfield-id "SF1234567890" --limit 5
      pyalex topics T1234567890
    """
    try:
        if topic_id:
            # Get specific topic
            topic = Topics()[topic_id]
            if _verbose_mode:
                typer.echo(f"[DEBUG] API URL: {Topics().url}/{topic_id}", err=True)
            _output_results(topic, output_format, single=True)
        else:
            # Search topics
            query = Topics()
            
            if search:
                query = query.search(search)
            if domain_id:
                query = query.filter(domain={"id": domain_id})
            if field_id:
                query = query.filter(field={"id": field_id})
            if subfield_id:
                query = query.filter(subfield={"id": subfield_id})
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def sources(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for sources"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'type', 'is_oa', 'country_code', "
             "'works_count', 'cited_by_count')"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    source_id: Annotated[Optional[str], typer.Argument(
        help="Specific source ID to retrieve"
    )] = None,
):
    """
    Search and retrieve sources (journals/venues) from OpenAlex.
    
    Examples:
      pyalex sources --search "Nature"
      pyalex sources --limit 5
      pyalex sources --group-by "type" --format table
      pyalex sources --group-by "is_oa" --search "machine learning"
      pyalex sources S1234567890
    """
    try:
        if source_id:
            # Get specific source
            source = Sources()[source_id]
            if _verbose_mode:
                typer.echo(f"[DEBUG] API URL: {Sources().url}/{source_id}", err=True)
            _output_results(source, output_format, single=True)
        else:
            # Search sources
            query = Sources()
            
            if search:
                query = query.search(search)
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                # For group-by operations, retrieve all groups by default
                if limit == 10:  # Default limit, get all groups
                    results = query.get()
                else:
                    results = query.get(limit=limit)
                
                _print_debug_results(results)
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def institutions(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for institutions"
    )] = None,
    country_code: Annotated[Optional[str], typer.Option(
        "--country",
        help="Filter by country code (e.g. US, UK, CA)"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_code', 'continent', "
             "'type', 'cited_by_count', 'works_count')"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    institution_id: Annotated[Optional[str], typer.Argument(
        help="Specific institution ID to retrieve"
    )] = None,
):
    """
    Search and retrieve institutions from OpenAlex.
    
    Examples:
      pyalex institutions --search "Harvard"
      pyalex institutions --country US --limit 5
      pyalex institutions --group-by "country_code"
      pyalex institutions --group-by "type" --format summary
      pyalex institutions I1234567890
    """
    try:
        if institution_id:
            # Get specific institution
            institution = Institutions()[institution_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Institutions().url}/{institution_id}", 
                    err=True
                )
            _output_results(institution, output_format, single=True)
        else:
            # Search institutions
            query = Institutions()
            
            if search:
                query = query.search(search)
            if country_code:
                query = query.filter(country_code=country_code)
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                try:
                    # For group-by operations, retrieve all groups by default
                    results = query.get(limit=100000)  # High limit to get all groups
                    _print_debug_results(results)
                except Exception as api_error:
                    typer.echo(f"[DEBUG] API call failed: {api_error}", err=True)
                    raise
                
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def publishers(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for publishers"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_codes', 'hierarchy_level', "
             "'works_count', 'cited_by_count')"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    publisher_id: Annotated[Optional[str], typer.Argument(
        help="Specific publisher ID to retrieve"
    )] = None,
):
    """
    Search and retrieve publishers from OpenAlex.
    
    Examples:
      pyalex publishers --search "Elsevier"
      pyalex publishers --limit 5
      pyalex publishers --group-by "country_codes" --format table
      pyalex publishers --group-by "hierarchy_level" --search "nature"
      pyalex publishers P1234567890
    """
    try:
        if publisher_id:
            # Get specific publisher
            publisher = Publishers()[publisher_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Publishers().url}/{publisher_id}", 
                    err=True
                )
            _output_results(publisher, output_format, single=True)
        else:
            # Search publishers
            query = Publishers()
            
            if search:
                query = query.search(search)
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                # For group-by operations, retrieve all groups by default
                if limit == 10:  # Default limit, get all groups
                    results = query.get()
                else:
                    results = query.get(limit=limit)
                
                _print_debug_results(results)
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def funders(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for funders"
    )] = None,
    group_by: Annotated[Optional[str], typer.Option(
        "--group-by",
        help="Group results by field (e.g. 'country_code', 'grants_count', "
             "'works_count', 'cited_by_count')"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    funder_id: Annotated[Optional[str], typer.Argument(
        help="Specific funder ID to retrieve"
    )] = None,
):
    """
    Search and retrieve funders from OpenAlex.
    
    Examples:
      pyalex funders --search "NSF"
      pyalex funders --limit 5
      pyalex funders --group-by "country_code" --format table
      pyalex funders --group-by "grants_count" --search "national"
      pyalex funders F1234567890
    """
    try:
        if funder_id:
            # Get specific funder
            funder = Funders()[funder_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Funders().url}/{funder_id}", 
                    err=True
                )
            _output_results(funder, output_format, single=True)
        else:
            # Search funders
            query = Funders()
            
            if search:
                query = query.search(search)
            
            # Handle group_by parameter
            if group_by:
                query = query.group_by(group_by)
                
                # Print debug URL before making the request
                _print_debug_url(query)
                
                # For group-by operations, retrieve all groups by default
                if limit == 10:  # Default limit, get all groups
                    results = query.get()
                else:
                    results = query.get(limit=limit)
                
                _print_debug_results(results)
                # Output grouped results
                _output_grouped_results(results, output_format)
                return
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def domains(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for domains"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    domain_id: Annotated[Optional[str], typer.Argument(
        help="Specific domain ID to retrieve"
    )] = None,
):
    """
    Search and retrieve domains from OpenAlex.
    
    Examples:
      pyalex domains --search "Physical Sciences"
      pyalex domains --limit 5
      pyalex domains D1234567890
    """
    try:
        if domain_id:
            # Get specific domain
            domain = Domains()[domain_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Domains().url}/{domain_id}", 
                    err=True
                )
            _output_results(domain, output_format, single=True)
        else:
            # Search domains
            query = Domains()
            
            if search:
                query = query.search(search)
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def fields(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for fields"
    )] = None,
    domain_id: Annotated[Optional[str], typer.Option(
        "--domain-id",
        help="Filter by domain OpenAlex ID"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    field_id: Annotated[Optional[str], typer.Argument(
        help="Specific field ID to retrieve"
    )] = None,
):
    """
    Search and retrieve fields from OpenAlex.
    
    Examples:
      pyalex fields --search "Computer Science"
      pyalex fields --domain-id "D1234567890" --limit 5
      pyalex fields F1234567890
    """
    try:
        if field_id:
            # Get specific field
            field = Fields()[field_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Fields().url}/{field_id}", 
                    err=True
                )
            _output_results(field, output_format, single=True)
        else:
            # Search fields
            query = Fields()
            
            if search:
                query = query.search(search)
            if domain_id:
                query = query.filter(domain={"id": domain_id})
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def subfields(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for subfields"
    )] = None,
    field_id: Annotated[Optional[str], typer.Option(
        "--field-id",
        help="Filter by field OpenAlex ID"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    subfield_id: Annotated[Optional[str], typer.Argument(
        help="Specific subfield ID to retrieve"
    )] = None,
):
    """
    Search and retrieve subfields from OpenAlex.
    
    Examples:
      pyalex subfields --search "Machine Learning"
      pyalex subfields --field-id "F1234567890" --limit 5
      pyalex subfields SF1234567890
    """
    try:
        if subfield_id:
            # Get specific subfield
            subfield = Subfields()[subfield_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Subfields().url}/{subfield_id}", 
                    err=True
                )
            _output_results(subfield, output_format, single=True)
        else:
            # Search subfields
            query = Subfields()
            
            if search:
                query = query.search(search)
            if field_id:
                query = query.filter(field={"id": field_id})
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def keywords(
    search: Annotated[Optional[str], typer.Option(
        "--search", "-s",
        help="Search term for keywords"
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit", "-l",
        help="Maximum number of results to return"
    )] = 10,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
    keyword_id: Annotated[Optional[str], typer.Argument(
        help="Specific keyword ID to retrieve"
    )] = None,
):
    """
    Search and retrieve keywords from OpenAlex.
    
    Examples:
      pyalex keywords --search "artificial intelligence"
      pyalex keywords --limit 5
      pyalex keywords cardiac-imaging
    """
    try:
        if keyword_id:
            # Get specific keyword
            keyword = Keywords()[keyword_id]
            if _verbose_mode:
                typer.echo(
                    f"[DEBUG] API URL: {Keywords().url}/{keyword_id}", 
                    err=True
                )
            _output_results(keyword, output_format, single=True)
        else:
            # Search keywords
            query = Keywords()
            
            if search:
                query = query.search(search)
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
            _print_debug_results(results)
            _output_results(results, output_format)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


def _output_results(results, output_format: str, single: bool = False):
    """Output results in the specified format."""
    # Handle None or empty results
    if results is None:
        typer.echo("No results found.")
        return
    
    if not single and (not results or len(results) == 0):
        typer.echo("No results found.")
        return
    
    if output_format == "json":
        if single:
            typer.echo(json.dumps(dict(results), indent=2))
        else:
            typer.echo(json.dumps([dict(r) for r in results], indent=2))
    elif output_format in ["title", "name"]:
        if single:
            result = results
            if 'display_name' in result:
                typer.echo(result['display_name'])
            elif 'title' in result:
                typer.echo(result['title'])
            else:
                typer.echo(result.get('id', 'Unknown'))
        else:
            for result in results:
                if 'display_name' in result:
                    typer.echo(result['display_name'])
                elif 'title' in result:
                    typer.echo(result['title'])
                else:
                    typer.echo(result.get('id', 'Unknown'))
    elif output_format == "table":
        _output_table(results, single)
    elif output_format == "summary":
        if single:
            typer.echo(f"\n[1] {_format_summary(results)}")
        else:
            for i, result in enumerate(results, 1):
                typer.echo(f"\n[{i}] {_format_summary(result)}")
    else:
        typer.echo(f"Unknown output format: {output_format}", err=True)
        raise typer.Exit(1) from None


def _output_table(results, single: bool = False):
    """Output results in table format using PrettyTable."""
    # Handle None results
    if results is None:
        typer.echo("No results found.")
        return
        
    if single:
        # For single items, wrap in a list for consistent processing
        results = [results]
    
    if not results:
        typer.echo("No results found.")
        return
    
    # Determine the type of entity based on the first result
    first_result = results[0]
    
    if 'publication_year' in first_result:  # Work
        table = PrettyTable()
        table.field_names = ["Name", "Year", "Journal", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            title = (result.get('display_name') or result.get('title') or 
                    'Unknown')[:MAX_WIDTH]
            year = result.get('publication_year', 'N/A')
            
            journal = 'N/A'
            if 'primary_location' in result and result['primary_location']:
                source = result['primary_location'].get('source', {})
                if source and source.get('display_name'):
                    journal = (source.get('display_name') or 'N/A')[:30]
            
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([title, year, journal, citations, openalex_id])
            
    elif ('works_count' in first_result and 
          ('last_known_institutions' in first_result or 
           'last_known_institution' in first_result)):
        # Author
        table = PrettyTable()
        table.field_names = ["Name", "Works", "Citations", "Institution", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            
            institution = 'N/A'
            # Handle new field (list) and old field (single object) for compatibility
            if result.get('last_known_institutions'):
                # New field: last_known_institutions is a list, take the first one
                institutions = result['last_known_institutions']
                if institutions and len(institutions) > 0:
                    inst = institutions[0]
                    institution = (inst.get('display_name') or 'Unknown')[:30]
            elif result.get('last_known_institution'):
                # Fallback for old field for backward compatibility
                inst = result['last_known_institution']
                institution = (inst.get('display_name') or 'Unknown')[:30]
            
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, works, citations, institution, openalex_id])
    
    elif 'country_code' in first_result:  # Institution
        table = PrettyTable()
        table.field_names = ["Name", "Country", "Works", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            country = result.get('country_code', 'N/A')
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, country, works, citations, openalex_id])
    
    elif 'issn' in first_result or 'issn_l' in first_result:  # Source/Journal
        table = PrettyTable()
        table.field_names = ["Name", "Type", "ISSN", "Works", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            source_type = result.get('type', 'N/A')
            issn = result.get('issn_l', result.get('issn', ['N/A']))
            if isinstance(issn, list):
                issn = issn[0] if issn else 'N/A'
            works = result.get('works_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, source_type, issn, works, openalex_id])
    
    elif 'hierarchy_level' in first_result:  # Publisher
        table = PrettyTable()
        table.field_names = ["Name", "Level", "Works", "Sources", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            level = result.get('hierarchy_level', 'N/A')
            works = result.get('works_count', 0)
            sources = result.get('sources_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, level, works, sources, openalex_id])
            
    elif 'works_count' in first_result:  # Topic, Domain, Field, Subfield, or Funder
        table = PrettyTable()
        table.field_names = ["Name", "Works", "Citations", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:50]
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, works, citations, openalex_id])
            
    else:  # Generic fallback
        table = PrettyTable()
        table.field_names = ["Name", "ID"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or result.get('title') or 
                   'Unknown')[:MAX_WIDTH]
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, openalex_id])
    
    typer.echo(table)


def _output_grouped_results(results, output_format: str):
    """Output grouped results in the specified format."""
    if results is None:
        typer.echo("No grouped results found.")
        return
    
    # When group-by is used, the results list itself contains the grouped data
    grouped_data = results
    
    if not grouped_data:
        typer.echo("No grouped results found.")
        return
    
    if output_format == "json":
        # Output the raw grouped data as JSON
        typer.echo(json.dumps([dict(item) for item in grouped_data], indent=2))
    elif output_format == "table":
        # Create a table for grouped results
        table = PrettyTable()
        table.field_names = ["Key", "Display Name", "Count"]
        table.max_width = MAX_WIDTH
        table.align = "l"
        
        for group in grouped_data:
            key = group.get('key', 'Unknown')
            display_name = group.get('key_display_name', key)
            count = group.get('count', 0)
            
            table.add_row([key, display_name, f"{count:,}"])
        
        typer.echo(table)
    elif output_format == "summary":
        # Output summary format
        total_count = sum(group.get('count', 0) for group in grouped_data)
        typer.echo(f"Total groups: {len(grouped_data)}")
        typer.echo(f"Total items: {total_count:,}")
        typer.echo()
        
        for i, group in enumerate(grouped_data, 1):
            key = group.get('key', 'Unknown')
            display_name = group.get('key_display_name', key)
            count = group.get('count', 0)
            percentage = (count / total_count * 100) if total_count > 0 else 0
            
            typer.echo(f"[{i}] {display_name}: {count:,} ({percentage:.1f}%)")
    elif output_format in ["title", "name"]:
        # Just output the group names
        for group in grouped_data:
            display_name = group.get('key_display_name') or group.get('key', 'Unknown')
            typer.echo(display_name)
    else:
        typer.echo(f"Unknown output format: {output_format}", err=True)
        raise typer.Exit(1) from None


def _format_summary(item):
    """Format a single item as a summary."""
    summary_parts = []
    
    # Display name or title
    name = item.get('display_name') or item.get('title', 'Unknown')
    summary_parts.append(f"Name: {name}")
    
    # ID
    if 'id' in item:
        summary_parts.append(f"ID: {item['id']}")
    
    # Type-specific information
    if 'publication_year' in item:  # Work
        summary_parts.append(f"Year: {item.get('publication_year', 'Unknown')}")
        if 'primary_location' in item and item['primary_location']:
            source = item['primary_location'].get('source', {})
            if source and source.get('display_name'):
                summary_parts.append(f"Journal: {source['display_name']}")
        if 'cited_by_count' in item:
            summary_parts.append(f"Citations: {item['cited_by_count']}")
        
        # Add abstract if available
        if 'abstract' in item and item['abstract']:
            abstract = item['abstract']
            abstract_preview = (abstract[:200] + "..." 
                              if len(abstract) > 200 else abstract)
            summary_parts.append(f"Abstract: {abstract_preview}")
    
    elif 'works_count' in item:  # Author or Topic
        summary_parts.append(f"Works: {item['works_count']}")
        if 'cited_by_count' in item:
            summary_parts.append(f"Citations: {item['cited_by_count']}")
        
        # Handle new field (list) and old field (single object) for compatibility
        if 'last_known_institutions' in item and item['last_known_institutions']:
            # New field: last_known_institutions is a list, take the first one
            institutions = item['last_known_institutions']
            if institutions and len(institutions) > 0:
                inst = institutions[0]
                summary_parts.append(
                    f"Institution: {inst.get('display_name', 'Unknown')}"
                )
        elif 'last_known_institution' in item and item['last_known_institution']:
            # Fallback for old field for backward compatibility
            inst = item['last_known_institution']
            summary_parts.append(
                f"Institution: {inst.get('display_name', 'Unknown')}"
            )
    
    return " | ".join(summary_parts)


@app.command()
def show(
    file_path: Annotated[Optional[str], typer.Argument(
        help="Path to the JSON file to display (if not provided, reads from stdin)"
    )] = None,
    output_format: Annotated[str, typer.Option(
        "--format", "-f",
        help="Output format: json, name, table, summary"
    )] = "table",
):
    """
    Display a JSON file containing OpenAlex data in table format.
    
    This command takes a JSON file saved from previous PyAlex queries
    and displays it in a human-readable format. If no file path is provided,
    it reads JSON data from stdin.
    
    Examples:
      pyalex show reviews.json
      pyalex show reviews.json --format summary
      pyalex show cited_by_reviews.json --format table
      cat reviews.json | pyalex show --format summary
      echo '{"display_name": "Test Work", "id": "W123"}' | pyalex show
    """
    try:
        # Read from file or stdin
        if file_path:
            # Check if file exists
            if not os.path.exists(file_path):
                typer.echo(f"Error: File '{file_path}' not found.", err=True)
                raise typer.Exit(1)
            
            # Read and parse JSON file
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON in file '{file_path}': {e}", err=True)
                raise typer.Exit(1) from e
            except Exception as e:
                typer.echo(f"Error reading file '{file_path}': {e}", err=True)
                raise typer.Exit(1) from e
        else:
            # Read from stdin
            import sys
            
            try:
                stdin_content = sys.stdin.read().strip()
                
                if not stdin_content:
                    typer.echo("Error: No input provided via stdin", err=True)
                    raise typer.Exit(1)
                
                # Parse JSON from stdin
                data = json.loads(stdin_content)
                
            except json.JSONDecodeError as e:
                typer.echo(f"Error: Invalid JSON from stdin: {e}", err=True)
                raise typer.Exit(1) from e
            except Exception as e:
                typer.echo(f"Error reading from stdin: {e}", err=True)
                raise typer.Exit(1) from e
        
        # Handle different data structures
        if isinstance(data, dict):
            # Single entity
            if _verbose_mode:
                source = f"file: {file_path}" if file_path else "stdin"
                typer.echo(
                    f"[DEBUG] Displaying single entity from {source}", 
                    err=True
                )
            _output_results(data, output_format, single=True)
        elif isinstance(data, list):
            # List of entities
            if _verbose_mode:
                source = f"file: {file_path}" if file_path else "stdin"
                typer.echo(
                    f"[DEBUG] Displaying {len(data)} entities from {source}", 
                    err=True
                )
            if not data:
                typer.echo("No data found in the input.")
                return
            _output_results(data, output_format, single=False)
        else:
            source = f"file '{file_path}'" if file_path else "stdin"
            typer.echo(
                f"Error: Unexpected data format from {source}. "
                f"Expected JSON object or array.", 
                err=True
            )
            raise typer.Exit(1) from None
            
    except typer.Exit:
        # Re-raise typer.Exit to maintain proper exit codes
        raise
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
