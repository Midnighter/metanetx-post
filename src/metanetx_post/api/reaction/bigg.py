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


"""Provide a high-level BiGG reaction API."""


import logging
from pathlib import Path
from typing import Dict, Set

import httpx
from cobra_component_models.orm import (
    Namespace,
    Reaction,
    ReactionAnnotation,
    ReactionName,
)
import pandas as pd
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ...model import BiGGUniversalReactionResult


__all__ = ("extract", "transform", "load")


logger = logging.getLogger(__name__)


Session = sessionmaker()


def extract(
    url: str = "http://bigg.ucsd.edu/api/v2/universal/reactions",
) -> str:
    """
    Fetch all BiGG universal reactions as JSON.

    Parameters
    ----------
    url : str, optional
        The URL to query for the BiGG universal reactions.

    Returns
    -------
    str
        The JSON response as string.

    Raises
    ------
    httpx.HTTPError
        In case the HTTP response status code was in the 400 or 500 range.

    """
    response = httpx.get(url)
    response.raise_for_status()
    # We return the response's `text` attribute (rather than the `raw` attribute) so
    # that the HTTP response body is already correctly encoded.
    return response.text


def transform(response: str) -> Dict[str, str]:
    """
    Generate a mapping of BiGG reaction identifiers to names.

    Parameters
    ----------
    response : str
        The JSON response containing BiGG universal reactions.

    Returns
    -------
    dict
        A map of BiGG reaction identifiers to names.

    Raises
    ------
    AssertionError
        If the response data is inconsistent.

    """
    data = BiGGUniversalReactionResult.parse_raw(response)
    assert len(data.results) == data.results_count
    return {r.bigg_id: r.name for r in data.results if r.name}


def load(
    session: Session, id2name: Dict[str, str], batch_size: int = 1000,
) -> None:
    """
    Return a BiGG universal reactions identifier to name mapping.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    filename : Path
        The BiGG universal reactions result.

    Returns
    -------
    dict
        A map from BiGG reaction identifiers to their names.

    """
    # Fetch all reactions from the database that have BiGG identifiers.
    bigg_ns: Namespace = session.query(Namespace).filter(
        Namespace.prefix == "bigg.reaction"
    ).one()
    query = (
        session.query(Reaction.id, ReactionAnnotation.identifier)
        .select_from(Reaction)
        .join(ReactionAnnotation)
        .join(Namespace)
        .filter(Namespace.id == bigg_ns.id)
    )
    df = pd.read_sql_query(query, session.bind)
    with tqdm(total=len(df), desc="BiGG Reaction") as pbar:
        for index in range(0, len(df), batch_size):
            mappings = []
            for row in df.iloc[index : index + batch_size].itertuples(index=False):
                name = id2name.get(row.identifier, None)
                if name is not None:
                    mappings.append(
                        {"reaction_id": row.id,
                         "namespace_id": bigg_ns.id,
                         "name": name,
                         }
                    )
            session.bulk_insert_mappings(ReactionName, mappings)
            session.commit()
            pbar.update(len(mappings))
