"""Entity identification and type detection utilities."""

import re
from typing import Union

from pyalex.entities.authors import Authors
from pyalex.entities.domains import Domains
from pyalex.entities.fields import Fields
from pyalex.entities.funders import Funders
from pyalex.entities.institutions import Institutions
from pyalex.entities.keywords import Keywords
from pyalex.entities.publishers import Publishers
from pyalex.entities.sources import Sources
from pyalex.entities.subfields import Subfields
from pyalex.entities.topics import Topics
from pyalex.entities.works import Works


def from_id(openalex_id: str) -> Union[dict, None]:
    """Get an OpenAlex entity from its ID with automatic type detection.
    
    This function analyzes the OpenAlex ID to determine the entity type
    and returns the appropriate entity object.
    
    Parameters
    ----------
    openalex_id : str
        The OpenAlex ID (e.g., 'W2741809807', 'A2208157607', etc.)
        
    Returns
    -------
    Union[dict, None]
        The OpenAlex entity object, or None if ID format is not recognized
        
    Examples
    --------
    >>> work = from_id('W2741809807')
    >>> author = from_id('A2208157607')
    >>> source = from_id('S2764455177')
    """
    # Clean the ID - remove URL prefix if present
    if openalex_id.startswith('https://openalex.org/'):
        openalex_id = openalex_id.replace('https://openalex.org/', '')
    
    # Pattern matching for different entity types
    if re.match(r'^W\d+$', openalex_id):
        # Work
        return Works()[openalex_id]
    elif re.match(r'^A\d+$', openalex_id):
        # Author
        return Authors()[openalex_id]
    elif re.match(r'^S\d+$', openalex_id):
        # Source (journal, conference, etc.)
        return Sources()[openalex_id]
    elif re.match(r'^I\d+$', openalex_id):
        # Institution
        return Institutions()[openalex_id]
    elif re.match(r'^T\d+$', openalex_id):
        # Topic
        return Topics()[openalex_id]
    elif re.match(r'^P\d+$', openalex_id):
        # Publisher
        return Publishers()[openalex_id]
    elif re.match(r'^F\d+$', openalex_id):
        # Funder
        return Funders()[openalex_id]
    elif re.match(r'^K\d+$', openalex_id):
        # Keyword
        return Keywords()[openalex_id]
    elif re.match(r'^domains/\d+$', openalex_id):
        # Domain
        domain_id = openalex_id.replace('domains/', '')
        return Domains()[domain_id]
    elif re.match(r'^fields/\d+$', openalex_id):
        # Field 
        field_id = openalex_id.replace('fields/', '')
        return Fields()[field_id]
    elif re.match(r'^subfields/\d+$', openalex_id):
        # Subfield
        subfield_id = openalex_id.replace('subfields/', '')
        return Subfields()[subfield_id]
    else:
        # Unknown ID format
        raise ValueError(f"Unknown OpenAlex ID format: {openalex_id}")


def get_entity_type(openalex_id: str) -> str:
    """Get the entity type from an OpenAlex ID.
    
    Parameters
    ---------- 
    openalex_id : str
        The OpenAlex ID
        
    Returns
    -------
    str
        The entity type ('work', 'author', 'source', etc.)
        
    Examples
    --------
    >>> get_entity_type('W2741809807')
    'work'
    >>> get_entity_type('A2208157607') 
    'author'
    """
    # Clean the ID - remove URL prefix if present
    if openalex_id.startswith('https://openalex.org/'):
        openalex_id = openalex_id.replace('https://openalex.org/', '')
    
    if re.match(r'^W\d+$', openalex_id):
        return 'work'
    elif re.match(r'^A\d+$', openalex_id):
        return 'author'
    elif re.match(r'^S\d+$', openalex_id):
        return 'source'
    elif re.match(r'^I\d+$', openalex_id):
        return 'institution'
    elif re.match(r'^T\d+$', openalex_id):
        return 'topic'
    elif re.match(r'^P\d+$', openalex_id):
        return 'publisher'
    elif re.match(r'^F\d+$', openalex_id):
        return 'funder'
    elif re.match(r'^K\d+$', openalex_id):
        return 'keyword'
    elif re.match(r'^domains/\d+$', openalex_id):
        return 'domain'
    elif re.match(r'^fields/\d+$', openalex_id):
        return 'field'
    elif re.match(r'^subfields/\d+$', openalex_id):
        return 'subfield'
    else:
        raise ValueError(f"Unknown OpenAlex ID format: {openalex_id}")
