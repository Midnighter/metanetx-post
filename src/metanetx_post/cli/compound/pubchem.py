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


"""Define the CLI for enriching compound information from PubChem."""


import json
import logging
from pathlib import Path

import click
from pandas import read_csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...api.compound import pubchem as pubchem_api
from ...model import PubChemCompoundModel
from ..helpers import JSON_SEPARATORS


logger = logging.getLogger(__name__)


Session = sessionmaker()


@click.group()
@click.help_option("--help", "-h")
def pubchem():
    """Subcommand for processing PubChem compounds."""
    pass


@pubchem.command()
@click.help_option("--help", "-h")
@click.argument(
    "filename", metavar="<FILENAME>", type=click.Path(dir_okay=False, exists=True)
)
@click.option(
    "--properties",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="pubchem_properties.json",
    show_default=True,
    help="The output path for the PubChem compound properties JSON response.",
)
@click.option(
    "--synonyms",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="pubchem_synonyms.json",
    show_default=True,
    help="The output path for the PubChem compound synonyms JSON response.",
)
def extract(filename: click.Path, properties: click.Path, synonyms: click.Path):
    """
    Fetch compound properties and synonyms from PubChem.

    \b
    FILENAME denotes the path to a comma-separated table with at least one column
    `compound_id` that contains `pubchem.compound:` prefixed identifiers.

    """
    df = read_csv(filename, header=0)
    df[["prefix", "identifier"]] = df["compound_id"].str.split(":", n=1, expand=True)
    identifiers = (
        df.loc[
            (df["prefix"] == "pubchem.compound") & df["identifier"].notnull(),
            "identifier",
        ]
        .unique()
        .tolist()
    )
    logger.info(f"Fetching {len(identifiers)} compounds from PubChem.")
    props, info = pubchem_api.extract(identifiers)
    with Path(properties).open("w") as handler:
        handler.write(props)
    with Path(synonyms).open("w") as handler:
        handler.write(info)


@pubchem.command()
@click.help_option("--help", "-h")
@click.argument(
    "properties", metavar="<PROPERTIES>", type=click.Path(dir_okay=False, exists=True)
)
@click.argument(
    "synonyms", metavar="<SYNONYMS>", type=click.Path(dir_okay=False, exists=True)
)
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True, exists=False),
    default="pubchem_compounds.json",
    show_default=True,
    help="The output path for the PubChem compounds JSON file.",
)
def transform(properties: click.Path, synonyms: click.Path, filename: click.Path):
    """
    Transform PubChem JSON responses to complete compound descriptions.

    \b
    PROPERTIES is the output path for PubChem compound properties.
    SYNONYMS is the output path for PubChem compound synonyms.

    """
    with Path(properties).open() as handle:
        properties = handle.read()
    with Path(synonyms).open() as handle:
        synonyms = handle.read()
    logger.info("Generating PubChem compound objects.")
    compounds = pubchem_api.transform(properties, synonyms)
    with Path(filename).open("w") as handle:
        json.dump([c.dict() for c in compounds], handle, separators=JSON_SEPARATORS)


@pubchem.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
@click.argument(
    "filename", metavar="<FILENAME>", type=click.Path(dir_okay=False, exists=True)
)
def load(db_uri: str, filename: click.Path):
    """
    Load PubChem compounds into the database.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.
    FILENAME is the path for the PubChem compound objects.

    """
    engine = create_engine(db_uri)
    session = Session(bind=engine)
    PubChemCompoundModel.Config.allow_population_by_field_name = True
    with Path(filename).open() as handle:
        compounds = [PubChemCompoundModel(**o) for o in json.load(handle)]
    logger.info("Adding PubChem compounds to the database.")
    pubchem_api.load(session, compounds)
