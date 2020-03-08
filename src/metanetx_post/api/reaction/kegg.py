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


import asyncio
import logging
from typing import Collection, Dict, Set

import pandas as pd
from cobra_component_models.orm import (
    Namespace,
    Reaction,
    ReactionAnnotation,
    ReactionName,
)
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ...etl import (
    KEGGReactionNameParser,
    fetch_kegg_list,
    fetch_kegg_resources,
    reaction_fetcher,
)
from ...model import KEGGResponsesModel
from ..helpers import summarize_responses


__all__ = ()


logger = logging.getLogger(__name__)


Session = sessionmaker()


def extract(url: str = "http://rest.kegg.jp/get/") -> pd.DataFrame:
    """
    Fetch all KEGG reaction descriptions.

    Parameters
    ----------
    url : str, optional
        The URL to query for the KEGG reactions.

    """
    loop = asyncio.get_event_loop()
    # Fetch a list of all KEGG reaction identifiers.
    reactions = loop.run_until_complete(fetch_kegg_list("reaction"))
    df = pd.read_csv(
        reactions, sep="\t", header=None, index_col=False, names=["id", "description"]
    )
    # We strip the prefix from the identifiers and use only unique occurrences.
    identifiers = df["id"].str[len("rn:") :].unique()
    data = loop.run_until_complete(
        fetch_kegg_resources(identifiers, reaction_fetcher, url)
    )
    loop.close()
    return data


def transform(response: str) -> Dict[str, Set[str]]:
    """
    Generate a mapping of KEGG reaction identifiers to names.

    Parameters
    ----------
    response : str
        The JSON collection of KEGG API responses containing reaction descriptions.

    Returns
    -------
    dict
        A map of KEGG reaction identifiers to names.

    Raises
    ------
    pydantic.ValidationError
        In case the JSON response data has an unexpected format.

    """
    data = KEGGResponsesModel.parse_raw(response)
    summarize_responses(data)
    return {
        response.identifier: names
        for response in tqdm(data.__root__, desc="Reaction")
        if response.status_code == 200
        and (names := KEGGReactionNameParser.parse(response.response))
    }


def load(
    session: Session, id2names: Dict[str, Collection[str]], batch_size: int = 1000,
) -> None:
    """
    Load KEGG reaction names into a database.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    id2names : dict
        A map of KEGG reaction identifiers to names.
    batch_size : int, optional
        The size of batches to process the data in.

    """
    # Fetch all reactions from the database that have KEGG identifiers.
    kegg_ns: Namespace = session.query(Namespace).filter(
        Namespace.prefix == "kegg.reaction"
    ).one()
    query = (
        session.query(Reaction.id, ReactionAnnotation.identifier)
        .select_from(Reaction)
        .join(ReactionAnnotation)
        .join(Namespace)
        .filter(Namespace.id == kegg_ns.id)
    )
    df = pd.read_sql_query(query.statement, session.bind)
    # Only unique names per reaction and namespace are allowed. Thus we group the
    # data by reaction index so that we can later make the names unique.
    grouped = df.groupby("id", as_index=False, sort=False)
    reaction_ids = df["id"].unique()
    with tqdm(total=len(reaction_ids), desc="Reaction") as pbar:
        for index in range(0, len(reaction_ids), batch_size):
            mappings = []
            batch = reaction_ids[index : index + batch_size]
            for rxn_id in batch:
                sub = grouped.get_group(rxn_id)
                # Create unique names per reaction.
                names = set()
                for seed_id in sub["identifier"]:
                    if labels := id2names.get(seed_id, None):
                        names.update(labels)
                # Apparently, `numpy.int` ends up as a BLOB in the database. We
                # convert to native `int` here.
                mappings.extend(
                    {"reaction_id": int(rxn_id), "namespace_id": kegg_ns.id, "name": n,}
                    for n in names
                )
            session.bulk_insert_mappings(ReactionName, mappings)
            session.commit()
            pbar.update(len(batch))
