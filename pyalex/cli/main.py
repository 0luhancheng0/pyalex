"""
Main CLI application for PyAlex.

This module contains the main typer app and global configuration.
"""

from typing import Annotated

import typer

from pyalex import config

from . import batch
from . import utils
from .commands.authors import create_authors_command
from .commands.entities import create_entity_commands
from .commands.funders import create_funders_command
from .commands.institutions import create_institutions_command
from .commands.utils import create_utils_commands
from .commands.works import create_works_command
from .commands.download import create_download_command
from .commands.extract import create_extract_command

from .commands.expand import create_expand_command
from .commands.network import create_network_command
from .commands.visualize_topics import create_topic_treemap_command

# Create the main typer app
app = typer.Typer(
    name="pyalex",
    help="CLI interface for the OpenAlex database",
    no_args_is_help=True,
)


# Global options
@app.callback()
def main(
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-d",
            help="Enable debug output including API URLs and internal details",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print a list of queries that would be run without executing them",
        ),
    ] = False,
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            help=f"Batch size for requests with multiple IDs "
            f"(default: {config.cli_batch_size})",
        ),
    ] = config.cli_batch_size,
):
    """
    PyAlex CLI - Access the OpenAlex database from the command line.

    OpenAlex doesn't require authentication for most requests.
    """
    # Set global state in submodules
    batch.set_global_state(debug, dry_run, batch_size)
    utils.set_global_state(debug, dry_run, batch_size)

    if debug:
        from pyalex.logger import setup_cli_logging

        logger = setup_cli_logging(debug=True)
        logger.debug(f"Email: {config.email}")
        logger.debug(f"User Agent: {config.user_agent}")
        logger.debug(
            "Debug mode enabled - API URLs and internal details will be displayed"
        )

    if dry_run:
        typer.echo(f"Dry run mode enabled - batch size: {batch_size}", err=True)

# Register all commands
create_works_command(app)
create_authors_command(app)
create_institutions_command(app)
create_funders_command(app)
create_utils_commands(app)
create_entity_commands(app)
create_download_command(app)
create_extract_command(app)

create_expand_command(app)
create_network_command(app)
create_topic_treemap_command(app)
