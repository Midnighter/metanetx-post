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
from typing import Type

from cobra_component_models.orm import Compound
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ...model import AbstractMoleculeAdapter


__all__ = ("augment_information",)


logger = logging.getLogger(__name__)


Session = sessionmaker()


def augment_information(
    session: Session,
    molecule_adapter: Type[AbstractMoleculeAdapter],
    batch_size: int = 1000,
) -> None:
    """
    Attempt to fill in missing structural information using chem-informatics software.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    molecule_adapter : AbstractMoleculeAdapter
    batch_size : int, optional
        The size of batches of compounds considered at a time (default 1000).

    """
    # We retrieve all compounds that either have an InChI or a SMILES description and
    # are missing at least one other piece of structural information.
    query = session.query(Compound).filter(
        or_(Compound.inchi.isnot(None), Compound.smiles.isnot(None)),
        or_(
            Compound.inchi_key.is_(None),
            Compound.chemical_formula.is_(None),
            Compound.mass.is_(None),
            Compound.charge.is_(None),
        ),
    )
    num_compounds = query.count()
    for compound in tqdm(
        query.yield_per(batch_size), total=num_compounds, desc="Compound"
    ):  # type: Compound
        if compound.inchi:
            logger.debug(compound.inchi)
            molecule = molecule_adapter.from_inchi(compound.inchi)
            if not molecule:
                continue
        elif compound.smiles:
            logger.debug(compound.smiles)
            if "*" in compound.smiles:
                logger.debug(
                    f"Refusing to convert unknown chemical groups to molecule."
                )
                continue
            molecule = molecule_adapter.from_smiles(compound.smiles)
            if not molecule:
                continue
        else:
            logger.error(
                "Wrong SQL query statement, this condition should be "
                "impossible to reach."
            )
            continue
        if not compound.inchi:
            compound.inchi = molecule.get_inchi()
        if not compound.inchi_key:
            compound.inchi_key = molecule.get_inchi_key()
        if not compound.smiles:
            compound.smiles = molecule.get_smiles()
        if not compound.chemical_formula:
            compound.chemical_formula = molecule.get_chemical_formula()
        if not compound.mass:
            compound.mass = molecule.get_molecular_mass()
        if not compound.charge:
            compound.charge = molecule.get_charge()
    # Keeping the commit out of the loop here assumes that the session can keep all
    # modified objects in memory.
    session.commit()
