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


"""Define the CLI for enriching reaction information."""


import json
import logging
from pathlib import Path

import click

from ..api import collect_bigg_reaction_names


logger = logging.getLogger(__name__)


@click.group()
@click.help_option("--help", "-h")
def reactions():
    """Subcommand for processing reactions."""
    pass


@reactions.command()
@click.help_option("--help", "-h")
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True),
    default="bigg_reaction_names.json",
    show_default=True,
    help="The output path for the BiGG reaction identifier to name JSON file.",
)
def collect_bigg_names(filename: click.Path):
    """
    Collect a mapping of BiGG reaction identifiers to names.

    \b
    FILENAME is the output path for the JSON result object.

    """
    output = Path(filename)
    result = collect_bigg_reaction_names()
    with output.open("w") as handle:
        json.dump(result, handle, allow_nan=False, separators=(",", ":"))
