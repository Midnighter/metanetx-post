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


"""Define the CLI for enriching ExPASy reaction information."""


import json
import logging
from pathlib import Path

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...api.reaction import expasy as expasy_api
from ..helpers import JSON_SEPARATORS, convert2json_type


logger = logging.getLogger(__name__)


Session = sessionmaker()


@click.group()
@click.help_option("--help", "-h")
def expasy():
    """Subcommands for processing ExPASy information."""
    pass


@expasy.command()
@click.help_option("--help", "-h")
@click.argument("email", metavar="<EMAIL>")
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True),
    default="enzyme.rdf",
    show_default=True,
    help="The output path for the ExPASy RDF file.",
)
def extract(email: str, filename: click.Path):
    """
    Fetch the ExPASy enzyme descriptions.

    \b
    EMAIL is required and is used to identify yourself to the ExPASy FTP server.

    """
    logger.info("Downloading enzyme descriptions from ExPASy.")
    # Unless we are debugging, we make the aioftp logger less noisy.
    if logger.getEffectiveLevel() > logging.DEBUG:
        logging.getLogger("aioftp").setLevel(logging.WARNING)
    expasy_api.extract(email, Path(filename))


@expasy.command()
@click.help_option("--help", "-h")
@click.argument("rdf", metavar="<RDF>", type=click.Path(dir_okay=False, exists=True))
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True),
    default="expasy_reaction_names.json",
    show_default=True,
    help="The output path for the ExPASy reaction identifier to name JSON file.",
)
@click.option(
    "--replacement",
    type=click.Path(dir_okay=False, writable=True),
    default="expasy_replacements.json",
    show_default=True,
    help="The output path for the EC-code replacement JSON file.",
)
def transform(rdf: click.Path, filename: click.Path, replacement: click.Path):
    """
    Generate a mapping of EC-codes to names and obsolete EC-codes.

    \b
    RDF The path on the local filesystem from where to load the RDF graph.

    """
    logger.info("Generating EC-code to name mapping and obsolete codes.")
    id2names, obsoletes = expasy_api.transform(Path(rdf))
    with Path(filename).open("w") as handle:
        json.dump(
            id2names, handle, default=convert2json_type, separators=JSON_SEPARATORS
        )
    with Path(replacement).open("w") as handle:
        json.dump(obsoletes, handle, separators=JSON_SEPARATORS)


@expasy.command()
@click.help_option("--help", "-h")
@click.argument("db-uri", metavar="<URI>")
@click.argument(
    "filename", metavar="<FILENAME>", type=click.Path(dir_okay=False, exists=True)
)
@click.argument(
    "replacement", metavar="<REPLACEMENT>", type=click.Path(dir_okay=False, exists=True)
)
def load(db_uri: str, filename: click.Path, replacement: click.Path):
    """
    Load EC-code names into a database.

    \b
    URI is a string interpreted as an rfc1738 compatible database URI.
    FILENAME is the EC-code to name mapping JSON file.
    REPLACEMENT is the EC-code replacment JSON file.

    """
    engine = create_engine(db_uri)
    session = Session(bind=engine)
    with Path(filename).open() as handle:
        id2name = json.load(handle)
    with Path(replacement).open() as handle:
        obsoletes = json.load(handle)
    logger.info("Adding EC-code names to database.")
    try:
        expasy_api.load(session, id2name, obsoletes)
    finally:
        session.close()
