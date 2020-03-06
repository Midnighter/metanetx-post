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


"""Define the CLI for augmenting compound information."""


import logging
import sys

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...api.compound import structure as structure_api


logger = logging.getLogger(__name__)


Session = sessionmaker()


@click.group()
@click.help_option("--help", "-h")
def structures():
    """Subcommands for augmenting compound structures."""
    pass


@structures.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
@click.option(
    "--backend",
    type=click.Choice(["rdkit", "openbabel"]),
    default="rdkit",
    show_default=True,
    help="The chem-informatics library to use for computing compound information.",
)
def etl(
    db_uri: str, backend: str,
):
    """
    Try to augment any missing structural compound information.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.

    """
    if backend == "rdkit":
        try:
            from ...model.rdkit_molecule_adapter import (
                RDKitMoleculeAdapter as MoleculeAdapter,
            )
        except ModuleNotFoundError:
            logger.critical(
                "Could not find an RDKit installation. Please install it, "
                "for example, with `pip install metanetx-post[rdkit]`."
            )
            sys.exit(1)
    elif backend == "openbabel":
        try:
            from ...model.rdkit_molecule_adapter import (
                RDKitMoleculeAdapter as MoleculeAdapter,
            )
        except ModuleNotFoundError:
            logger.critical(
                "Could not find an Open Babel installation. Please install it, "
                "for example, with `pip install metanetx-post[openbabel]`."
            )
            sys.exit(1)
    else:
        logger.critical("No chem-informatics backend available. Aborting.")
        sys.exit(1)

    engine = create_engine(db_uri)
    session = Session(bind=engine)
    structure_api.augment_information(session, MoleculeAdapter)
