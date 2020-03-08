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


import json
import logging
import sys
from pathlib import Path

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...api.compound import kegg as kegg_api
from ..helpers import JSON_SEPARATORS


logger = logging.getLogger(__name__)


Session = sessionmaker()


@click.group()
@click.help_option("--help", "-h")
def kegg():
    """Subcommand for processing compounds."""
    pass


@kegg.command()
@click.help_option("--help", "-h")
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="kegg_compounds.json",
    show_default=True,
    help="The output path for the KEGG MDL MOL blocks.",
)
def extract(filename: click.Path):
    """Fetch MDL MOL blocks for all compounds in KEGG."""
    logger.info("Downloading KEGG MDL MOL blocks.")
    result = kegg_api.extract()
    result.to_json(filename, orient="records")


@kegg.command()
@click.help_option("--help", "-h")
@click.argument(
    "response", metavar="<RESPONSE>", type=click.Path(dir_okay=False, exists=True)
)
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="kegg_inchi.json",
    show_default=True,
    help="The output path for the KEGG compound identifier to InChI JSON file.",
)
@click.option(
    "--backend",
    type=click.Choice(["rdkit", "openbabel"]),
    default="rdkit",
    show_default=True,
    help="The chem-informatics library to use for computing compound information.",
)
def transform(response: click.Path, filename: click.Path, backend: str):
    """
    Generate a mapping from KEGG compound identifiers to InChIs.

    \b
    RESPONSE is the JSON response containing KEGG universal expasy.

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
    logger.info("Generating compounds from KEGG MDL MOL blocks.")
    with Path(response).open() as handle:
        id2inchi = kegg_api.transform(handle.read(), MoleculeAdapter)
    with Path(filename).open("w") as handle:
        json.dump(id2inchi, handle, separators=JSON_SEPARATORS)


@kegg.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
@click.argument(
    "filename", metavar="<FILENAME>", type=click.Path(dir_okay=False, exists=True)
)
@click.option(
    "--report",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="kegg_inchi_conflicts.json",
    show_default=True,
    help="The output path for compound conflicts related to KEGG InChIs.",
)
def load(db_uri: str, filename: click.Path, report: click.Path):
    """
    Load KEGG reaction names into a database.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.
    FILENAME is the KEGG compound identifier to InChI mapping JSON file.

    """
    engine = create_engine(db_uri)
    session = Session(bind=engine)
    with Path(filename).open() as handle:
        id2inchi = json.load(handle)
    logger.info("Adding KEGG compound InChIs to the database.")
    try:
        conflicts = kegg_api.load(session, id2inchi)
    finally:
        session.close()
    with Path(report).open("w") as handle:
        handle.write(conflicts.json())
