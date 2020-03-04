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
from typing import Any, Coroutine, Optional, Tuple

import httpx
from cobra_component_models.orm import Compound
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ..model import AbstractMoleculeAdapter


__all__ = ("kegg_mol_fetcher",)


logger = logging.getLogger(__name__)


Session = sessionmaker()


def kegg_mol_fetcher(
    identifier: str, client: httpx.AsyncClient
) -> Coroutine[Any, Any, httpx.Response]:
    """
    Prepare an asynchronous HTTP call to retrieve a KEGG MDL MOL block.

    Parameters
    ----------
    identifier : str
        The KEGG compound identifier.
    client : httpx.AsyncClient
        An httpx asynchronous client with a `base_url` set.

    Returns
    -------
    coroutine
        A `client.get` call that can be awaited by the caller of this function.

    """
    return client.get(f"{identifier}/mol")


# def populate_additional_compounds(session, filename) -> None:
#     """Populate the database with additional compounds."""
#     additional_compound_df = pd.read_csv(filename)
#     additional_compound_df[additional_compound_df.isnull()] = None
#     name_registry = session.query(Registry).filter_by(namespace="synonyms").one()
#     coco_registry = session.query(Registry).filter_by(namespace="coco").one()
#     for row in tqdm(additional_compound_df.itertuples(index=False)):
#         if session.query(exists().where(Compound.inchi == row.inchi)).scalar():
#             continue
#         logger.info(f"Adding non-MetaNetX compound: {row.name}")
#         compound = Compound(
#             mnx_id=row.mnx_id, inchi=row.inchi, inchi_key=inchi_to_inchi_key(row.inchi)
#         )
#         identifiers = []
#         if row.coco_id:
#             print(repr(row.coco_id))
#             identifiers.append(
#                 CompoundIdentifier(registry=coco_registry, accession=row.coco_id)
#             )
#         if row.name:
#             identifiers.append(
#                 CompoundIdentifier(registry=name_registry, accession=row.name)
#             )
#         compound.identifiers = identifiers
#         session.add(compound)
#     session.commit()
