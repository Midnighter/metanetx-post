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


"""Define the main entry point for the command line interface (CLI)."""


import logging
import os
from pathlib import Path

import click
import click_log

from ..api import fetch_bigg_info, fetch_kegg_info


logger = logging.getLogger()
click_log.basic_config(logger)


NUM_PROCESSES = os.cpu_count()
if NUM_PROCESSES is None:
    logger.warning("Could not determine the number of cores available - assuming 1.")
    NUM_PROCESSES = 1
elif NUM_PROCESSES > 1:
    # By default leave one core free for interactive user tasks.
    NUM_PROCESSES -= 1


@click.group()
@click.help_option("--help", "-h")
@click_log.simple_verbosity_option(
    logger,
    default="INFO",
    show_default=True,
    type=click.Choice(["CRITICAL", "ERROR", "WARN", "INFO", "DEBUG"]),
)
def cli():
    """Command line interface to load the MetaNetX content into data models."""
    pass


@cli.command()
@click.help_option("--help", "-h")
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True),
    default="kegg_info.txt",
    show_default=True,
    help="The output path for the KEGG information file.",
)
def kegg_info(filename: click.Path):
    """Retrieve the KEGG database version information."""
    output = Path(filename)
    with output.open("w") as handle:
        handle.write(fetch_kegg_info())


@cli.command()
@click.help_option("--help", "-h")
@click.option(
    "--filename",
    "-f",
    type=click.Path(dir_okay=False, writable=True),
    default="bigg_info.json",
    show_default=True,
    help="The output path for the BiGG information file.",
)
def bigg_info(filename: click.Path):
    """Retrieve the BiGG database version information."""
    output = Path(filename)
    model = fetch_bigg_info()
    with output.open("w") as handle:
        handle.write(model.json())


# TODO: SEED

# TODO: Expasy

# try:
#     if compress:
#         handle = gzip.open(local_filename, mode="wb")
#     else:
#         handle = local_filename.open("wb")
#     transferred = 0
#     # TODO (Moritz): May want to increase the socket timeout here.
#     async with client.download_stream(filename) as stream:
#         async for block in stream.iter_by_block():
#             handle.write(block)
#             transferred += len(block)
#     assert transferred == info.size, "Not all bytes were transferred."
# except IOError as error:
#     logger.error("Failed to download '%s'.", filename)
#     logger.debug("", exc_info=error)
# finally:
#     handle.close()
