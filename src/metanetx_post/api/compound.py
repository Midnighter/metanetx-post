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

from cobra_component_models.orm import Compound, CompoundAnnotation, Namespace
from pandas import DataFrame, read_sql_query
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ..etl import fetch_resources, kegg_mol_fetcher


__all__ = ("collect_mol_from_kegg",)


logger = logging.getLogger(__name__)


Session = sessionmaker()


def collect_mol_from_kegg(session: Session) -> DataFrame:
    """
    Collect MDL MOL files from KEGG for compounds without InChI.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.

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
    loop = asyncio.get_event_loop()
    try:
        data = loop.run_until_complete(
            fetch_resources(
                df["identifier"].unique(), "http://rest.kegg.jp/get/", kegg_mol_fetcher
            )
        )
    finally:
        loop.stop()
        loop.close()
    return data


def add_inchi_from_kegg():
    # The resulting data frame will contain duplicate compound primary keys.
    primary_keys = df["id"].unique()
    logger.info(
        f"There are {len(primary_keys)} KEGG compounds missing an InChI " f"string."
    )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(collect_missing_inchi(df))
    finally:
        loop.stop()
        loop.close()
    num_inchi = len(df.loc[df["inchi"].notnull(), "id"].unique())
    logger.info(f"{num_inchi} new InChI strings were collected from KEGG.")
    grouped_df = df.groupby("id", sort=False)
    with tqdm(total=len(primary_keys), desc="KEGG Compound") as pbar:
        for index in range(0, len(primary_keys), batch_size):
            mappings = []
            for key in primary_keys.iloc[index : index + batch_size]:
                sub = grouped_df.get_group(key)
                mask = sub["inchi"].notnull()
                if mask.sum() == 0:
                    mappings.append({"id": key, "inchi": None})
                else:
                    mappings.append({"id": key, "inchi": sub.loc[mask, "inchi"].iat[0]})
            session.bulk_update_mappings(Compound, mappings)
            pbar.update(len(mappings))
