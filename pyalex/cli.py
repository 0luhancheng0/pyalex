#!/usr/bin/env python3
"""
PyAlex CLI - Command line interface for the OpenAlex database
"""
import json
from typing import Optional

import typer
from prettytable import PrettyTable
from typing_extensions import Annotated

from pyalex import Authors
from pyalex import Domains
from pyalex import Fields
from pyalex import Funders
from pyalex import Institutions
from pyalex import Publishers
from pyalex import Sources
from pyalex import Subfields
from pyalex import Topics
from pyalex import Works
from pyalex import config


# Global verbose state
_verbose_mode = False


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
      pyalex works W1234567890
    """
    try:
        if work_id:
            # Get specific work
            work = Works()[work_id]
            if _verbose_mode:
                typer.echo(f"[DEBUG] API URL: {Works().url}/{work_id}", err=True)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            
            try:
                results = query.get(limit=limit)
                if _verbose_mode:
                    typer.echo(f"[DEBUG] Results type: {type(results)}", err=True)
                    if hasattr(results, '__len__'):
                        typer.echo(f"[DEBUG] Results length: {len(results)}", err=True)
            except Exception as api_error:
                typer.echo(f"[DEBUG] API call failed: {api_error}", err=True)
                raise
            
            # Check if results is None or empty
            if results is None:
                typer.echo("No results returned from API", err=True)
                return
                
            _output_results(results, output_format)
            
    except Exception as e:
        if _verbose_mode:
            import traceback
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
                query = query.filter(last_known_institution={"id": institution_id})
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
            
            # Print debug URL before making the request
            _print_debug_url(query)
            results = query.get(limit=limit)
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
        table.max_width = 60
        table.align = "l"
        
        for result in results:
            title = (result.get('display_name') or result.get('title') or 
                    'Unknown')[:60]
            year = result.get('publication_year', 'N/A')
            
            journal = 'N/A'
            if 'primary_location' in result and result['primary_location']:
                source = result['primary_location'].get('source', {})
                if source and source.get('display_name'):
                    journal = (source.get('display_name') or 'N/A')[:30]
            
            citations = result.get('cited_by_count', 0)
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([title, year, journal, citations, openalex_id])
            
    elif 'works_count' in first_result and 'last_known_institution' in first_result:
        # Author
        table = PrettyTable()
        table.field_names = ["Name", "Works", "Citations", "Institution", "ID"]
        table.max_width = 60
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or 'Unknown')[:40]
            works = result.get('works_count', 0)
            citations = result.get('cited_by_count', 0)
            
            institution = 'N/A'
            if result.get('last_known_institution'):
                inst = result['last_known_institution']
                institution = (inst.get('display_name') or 'Unknown')[:30]
            
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, works, citations, institution, openalex_id])
    
    elif 'country_code' in first_result:  # Institution
        table = PrettyTable()
        table.field_names = ["Name", "Country", "Works", "Citations", "ID"]
        table.max_width = 60
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
        table.max_width = 60
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
        table.max_width = 60
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
        table.max_width = 60
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
        table.max_width = 60
        table.align = "l"
        
        for result in results:
            name = (result.get('display_name') or result.get('title') or 
                   'Unknown')[:60]
            openalex_id = result.get('id', '').split('/')[-1]
            
            table.add_row([name, openalex_id])
    
    typer.echo(table)


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
    
    elif 'works_count' in item:  # Author or Topic
        summary_parts.append(f"Works: {item['works_count']}")
        if 'cited_by_count' in item:
            summary_parts.append(f"Citations: {item['cited_by_count']}")
        if 'last_known_institution' in item and item['last_known_institution']:
            # Author
            inst = item['last_known_institution']
            summary_parts.append(f"Institution: {inst.get('display_name', 'Unknown')}")
    
    return " | ".join(summary_parts)


if __name__ == "__main__":
    app()
