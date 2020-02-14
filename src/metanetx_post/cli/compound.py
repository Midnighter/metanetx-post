# Copyright (c) 2020, Moritz E. Beber.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Define the CLI for enriching compound information."""


import logging

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..api import collect_mol_from_kegg


logger = logging.getLogger(__name__)


Session = sessionmaker()


@click.group()
@click.help_option("--help", "-h")
def compounds():
    """Subcommand for processing compounds."""
    pass


@compounds.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
@click.argument(
    "filename", metavar="<FILENAME>", type=click.Path(dir_okay=False, writable=True)
)
def collect_kegg_mol(db_uri: str, filename: click.Path):
    """
    Collect MDL MOL files from KEGG for compounds without InChI.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.
    FILENAME is the output path for the JSON result object.

    """
    engine = create_engine(db_uri)
    session = Session(bind=engine)
    result = collect_mol_from_kegg(session)
    result.to_json(filename, orient="records")


@compounds.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
def add_information(db_uri: str,):
    """
    Add any missing structural compound information.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.

    """
    # We import within the function due to the openbabel requirement.
    from ..etl.compound import add_missing_information

    engine = create_engine(db_uri)
    session = Session(bind=engine)
    add_missing_information(session)
