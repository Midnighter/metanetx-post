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


"""Provide a high-level ExPASy reaction API."""


import asyncio
import logging
from pathlib import Path
from typing import Collection, Dict, Set, Tuple

import pandas as pd
from cobra_component_models.orm import (
    Namespace,
    Reaction,
    ReactionAnnotation,
    ReactionName,
)
from rdflib import Graph
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ...etl import collect_expasy_names, collect_expasy_obsoletes, fetch_expasy_rdf


__all__ = ()


logger = logging.getLogger(__name__)


Session = sessionmaker()


def extract(email: str, filename: Path) -> None:
    """
    Fetch the ExPASy RDF description of enzymes.

    Parameters
    ----------
    email : str
        An email string used to identify yourself to the FTP server.
    filename: pathlib.Path
        The full path where to store the RDF file.

    """
    with_debug = logger.getEffectiveLevel() <= logging.DEBUG
    asyncio.run(fetch_expasy_rdf(email, filename), debug=with_debug)


def transform(filename: Path,) -> Tuple[Dict[str, Set[str]], Dict[str, str]]:
    """
    Collect ExPASy EC-code descriptions.

    Parameters
    ----------
    filename : pathlib.Path
        The path on the local filesystem from where to load the RDF graph.

    Returns
    -------
    tuple
        A pair of dictionaries, the first mapping EC codes to names and the second
        mapping obsolete EC codes to their replacements.

    """
    graph = Graph()
    graph.parse(str(filename))
    return collect_expasy_names(graph), collect_expasy_obsoletes(graph)


def load(
    session: Session,
    id2names: Dict[str, Collection[str]],
    obsoletes: Dict[str, str],
    batch_size: int = 1000,
) -> None:
    """
    Load EC-code names into a database.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    id2names : dict
        A map of EC-codes to names.
    obsoletes : dict
        A map of obsolete EC-codes to their replacements.
    batch_size : int, optional
        The size of batches to proces the data in.

    """
    # Fetch all reactions from the database that have EC-codes.
    ec_code_ns: Namespace = session.query(Namespace).filter(
        Namespace.prefix == "ec-code"
    ).one()
    query = (
        session.query(Reaction.id, ReactionAnnotation.identifier)
        .select_from(Reaction)
        .join(ReactionAnnotation)
        .join(Namespace)
        .filter(Namespace.id == ec_code_ns.id)
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
                # Check if any EC-code is obsolete and has a replacement.
                ec_codes = [obsoletes.get(e, e) for e in sub["identifier"]]
                # Create unique names per reaction.
                names = set()
                for code in ec_codes:
                    if labels := id2names.get(code, None):
                        names.update(labels)
                # Apparently, `numpy.int` ends up as a BLOB in the database. We
                # convert to native `int` here.
                mappings.extend(
                    {
                        "reaction_id": int(rxn_id),
                        "namespace_id": ec_code_ns.id,
                        "name": n,
                    }
                    for n in names
                )
            session.bulk_insert_mappings(ReactionName, mappings)
            session.commit()
            pbar.update(len(batch))
