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

import click
import click_log


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
