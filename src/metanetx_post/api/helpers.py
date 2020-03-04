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


"""Populate compound information."""


import logging
from collections import Counter

import httpx
from sqlalchemy.orm import sessionmaker

from ..model import BiGGVersionModel, KEGGResponsesModel


__all__ = ("fetch_kegg_info", "fetch_bigg_info", "summarize_responses")


logger = logging.getLogger(__name__)


Session = sessionmaker()


def fetch_kegg_info() -> str:
    """Fetch the KEGG database version information."""
    response = httpx.get("http://rest.kegg.jp/info/kegg")
    response.raise_for_status()
    return response.text


def fetch_bigg_info() -> BiGGVersionModel:
    """Fetch the BiGG database version information."""
    response = httpx.get("http://bigg.ucsd.edu/api/v2/database_version")
    response.raise_for_status()
    # We use the response's `text` attribute (rather than the `raw` attribute) so that
    # the HTTP response body is already correctly encoded.
    return BiGGVersionModel.parse_raw(response.text)


def summarize_responses(responses: KEGGResponsesModel) -> None:
    logger.info("HTTP responses status code summary:")
    summary = Counter(response.status_code for response in responses.__root__)
    for code, num in summary.items():
        logger.info(f"{code}: {num} ({num / len(responses.__root__):.2%})")
