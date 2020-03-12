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


import asyncio
import logging
from collections import Counter
from typing import Dict, Type

from cobra_component_models.orm import (
    BiologyQualifier,
    Compound,
    CompoundAnnotation,
    Namespace,
)
from cobra_component_models.serializer import CompoundSerializer
from pandas import DataFrame, read_csv, read_sql_query
from sqlalchemy.orm import selectinload, sessionmaker
from tqdm import tqdm

from ...etl import fetch_kegg_list, fetch_kegg_resources, kegg_mol_fetcher
from ...model import (
    AbstractMoleculeAdapter,
    InChIConflict,
    InChIConflictReport,
    KEGGResponsesModel,
)
from ..helpers import summarize_responses


__all__ = ("extract", "transform", "load")


logger = logging.getLogger(__name__)


Session = sessionmaker()


def extract(url: str = "http://rest.kegg.jp/get/",) -> DataFrame:
    """
    Fetch MDL MOL blocks from KEGG for compounds without InChI.

    Parameters
    ----------
    url : str, optional
        The URL to query for the KEGG compounds.

    Returns
    -------
    pandas.DataFrame
        A data frame with two columns, the compound index and its corresponding KEGG
        identifier.

    """
    loop = asyncio.get_event_loop()
    identifiers = set()
    for db, prefix in [
        ("compound", "cpd:"),
        ("glycan", "gl:"),
        ("drug", "dr:"),
        ("environ", "ev:"),
    ]:
        text = loop.run_until_complete(fetch_kegg_list(db))
        df = read_csv(
            text, sep="\t", header=None, index_col=False, names=["id", "description"]
        )
        # We strip the prefix from the identifiers and use only unique occurrences.
        identifiers.update(df["id"].str[len(prefix) :].unique())
    data = loop.run_until_complete(
        fetch_kegg_resources(identifiers, kegg_mol_fetcher, url)
    )
    loop.close()
    return data


def transform(
    response: str, molecule_adapter: Type[AbstractMoleculeAdapter]
) -> Dict[str, str]:
    """
    Transform the KEGG MDL MOL blocks to compound information.

    Parameters
    ----------
    response : str
        The JSON collection of KEGG API responses containing reaction descriptions.
    molecule_adapter : AbstractMoleculeAdapter

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
        response.identifier: inchi
        for response in tqdm(data.__root__, desc="MOL Block")
        if response.status_code == 200
        and (molecule := molecule_adapter.from_mol_block(response.response))
        and (inchi := molecule.get_inchi())
    }


def load(
    session: Session, id2inchi: Dict[str, str], batch_size: int = 1000,
) -> InChIConflictReport:
    """
    Attempt to add InChI strings from KEGG to the database.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    id2inchi : dict
        A mapping from KEGG identifiers to InChI strings.
    batch_size : int, optional
        The size of batches to proces the data in (default 1000). This can optimize
        the speed to interact with the database.

    """
    # Fetch all compounds from the database that have KEGG identifiers and are
    # missing their InChI string.
    query = (
        session.query(Compound.id, CompoundAnnotation.identifier)
        .select_from(Compound)
        .join(CompoundAnnotation)
        .join(Namespace)
        .filter(Namespace.prefix.like("kegg%"))
        .filter(Compound.inchi.is_(None))
    )
    df = read_sql_query(query.statement, session.bind)
    # The resulting data frame will contain duplicate compound primary keys.
    primary_keys = df["id"].unique()
    logger.info(
        f"There are {len(primary_keys)} compounds with KEGG identifiers that are "
        f"missing an InChI string."
    )
    grouped_df = df.groupby("id", sort=False)
    serializer = CompoundSerializer(
        biology_qualifiers=BiologyQualifier.get_map(session),
        namespaces=Namespace.get_map(session),
    )
    conflicts = []
    with tqdm(total=len(primary_keys), desc="Compound") as pbar:
        for index in range(0, len(primary_keys), batch_size):
            mappings = []
            batch = primary_keys[index : index + batch_size]
            for key in batch:
                sub = grouped_df.get_group(key)
                inchis = {
                    inchi
                    for kegg_id in sub["identifier"]
                    if (inchi := id2inchi.get(kegg_id, None))
                }
                if not inchis:
                    continue
                # We create information for detailed conflicts here.
                conflict = InChIConflict(
                    candidate_compound=serializer.serialize(
                        session.query(Compound)
                        .options(selectinload(Compound.annotation))
                        .options(selectinload(Compound.names))
                        .filter(Compound.id == int(key))
                        .one()
                    ),
                    kegg_inchis=list(inchis),
                    existing_compounds=[],
                )
                for inchi in inchis:
                    alternative = (
                        session.query(Compound)
                        .options(selectinload(Compound.annotation))
                        .options(selectinload(Compound.names))
                        .filter(Compound.inchi == inchi)
                        .one_or_none()
                    )
                    if alternative:
                        conflict.existing_compounds.append(
                            serializer.serialize(alternative)
                        )
                # If the data is conflicting we do not try to resolve it but simply
                # collect a report.
                if len(conflict.existing_compounds) > 0 or len(inchis) > 1:
                    conflicts.append(conflict)
                    continue
                # We are certain here that `inchis` is a set with one element.
                inchi = inchis.pop()
                mappings.append({"id": int(key), "inchi": inchi})
            pbar.update(len(batch))
    logger.info(f"There are {len(mappings)} potentially new InChIs from KEGG.")
    inchi_hist = Counter((m["inchi"] for m in mappings))
    updates = [m for m in mappings if inchi_hist[m["inchi"]] == 1]
    session.bulk_update_mappings(Compound, updates)
    session.commit()
    logger.info(f"{len(updates)} additional InChI strings were added from KEGG.")
    duplicates = {}
    for mapping in mappings:
        inchi = mapping["inchi"]
        if inchi_hist[inchi] > 1:
            duplicates.setdefault(inchi, []).append(
                serializer.serialize(
                    session.query(Compound)
                    .options(selectinload(Compound.annotation))
                    .options(selectinload(Compound.names))
                    .filter(Compound.id == mapping["id"])
                    .one()
                )
            )
    logger.info(f"There are {len(duplicates)} InChIs with duplicates in KEGG.")
    logger.info(f"There are {len(conflicts)} conflicts.")
    return InChIConflictReport(conflicts=conflicts, duplicates=duplicates)
