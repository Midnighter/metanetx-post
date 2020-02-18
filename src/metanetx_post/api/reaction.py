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


"""Populate reaction information."""


import logging
from typing import Dict

import httpx

from ..model import BiGGUniversalReactionResult


__all__ = ("collect_bigg_reaction_names",)


logger = logging.getLogger(__name__)


def collect_bigg_reaction_names(
    url: str = "http://bigg.ucsd.edu/api/v2/universal/reactions",
) -> Dict[str, str]:
    """
    Collect all BiGG universal reactions and return an identifier to name mapping.

    Parameters
    ----------
    url : str, optional
        The URL to query for the BiGG universal reactions.

    Returns
    -------
    dict
        A map from BiGG reaction identifiers to their names.

    Raises
    ------
    httpx.HTTPError
        In case the HTTP response status code was in the 400 or 500 range.

    """
    response = httpx.get(url)
    response.raise_for_status()
    # We use the response's `text` attribute (rather than the `raw` attribute) so that
    # the HTTP response body is already correctly encoded.
    data = BiGGUniversalReactionResult.parse_raw(response.text)
    assert len(data.results) == data.results_count
    return {r.bigg_id: r.name for r in data.results if r.name}
