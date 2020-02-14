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
from openbabel import openbabel as ob
from openbabel import pybel
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm


__all__ = ("kegg_mol_fetcher",)


# Disable the Open Babel logging. Unfortunately, we cannot redirect the stream
# which would be preferable.
ob.obErrorLog.SetOutputLevel(-1)


logger = logging.getLogger(__name__)


Session = sessionmaker()


def kegg_mol_fetcher(
    identifier: str, client: httpx.AsyncClient
) -> Coroutine[Any, Any, httpx.Response]:
    """

    Parameters
    ----------
    identifier
    client

    Returns
    -------

    """
    return client.get(f"{identifier}/mol")


async def transform_mol2inchi(
    index: int, identifier: str, client: httpx.AsyncClient
) -> Tuple[int, Optional[str]]:
    """
    Fetch a single mol description of a compound from KEGG and convert it to InChI.

    Parameters
    ----------
    index : int
        The underlying data frame index.
    identifier : str
        The KEGG identifier.
    client : httpx.AsyncClient
        An httpx asynchronous client with a `base_url` set.

    Returns
    -------
    tuple
        A pair of index and InChI string or index and `None` if there was a connection
        error.

    """
    try:
        molecule = pybel.readstring("mol", response.text)
        inchi = molecule.write("inchi").strip()
    except IOError as error:
        logger.debug(f"{identifier}: {str(error)}")
        inchi = None
    if inchi:
        return index, inchi
    else:
        return index, None


def add_missing_information(session: Session, batch_size: int = 1000,) -> None:
    """
    Fill in missing structural information using openbabel.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    batch_size : int, optional
        The size of batches of compounds considered at a time (default 1000).

    """
    query = session.query(Compound).filter(Compound.inchi.isnot(None))
    num_compounds = query.count()
    for compound in tqdm(
        query.yield_per(batch_size), total=num_compounds, desc="Compound"
    ):  # type: Compound
        # If all structural data exists, we can skip this compound.
        if (
            compound.inchi_key
            and compound.smiles
            and compound.chemical_formula
            and compound.mass
            and compound.charge
        ):
            continue
        else:
            try:
                logger.debug(compound.inchi)
                molecule: pybel.Molecule = pybel.readstring("inchi", compound.inchi)
            except IOError as error:
                logger.error(
                    f"Open Babel failed to read InChI for compound " f"{compound.id}."
                )
                logger.debug("", exc_info=error)
                continue
        if not compound.inchi_key:
            compound.inchi_key = molecule.write("inchikey").strip()
        if not compound.smiles:
            compound.smiles = molecule.write("smiles").strip()
        if not compound.chemical_formula:
            compound.chemical_formula = molecule.formula
        if not compound.mass:
            compound.mass = molecule.molwt
        if not compound.charge:
            compound.charge = molecule.charge
    # Keeping the commit out of the loop here assumes that the session can keep all
    # modified objects in memory.
    session.commit()


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
