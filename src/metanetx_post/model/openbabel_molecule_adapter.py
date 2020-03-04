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


"""Provide an abstract molecule adapter class."""


from __future__ import annotations

import logging
from typing import Optional

from openbabel import openbabel as ob
from openbabel import pybel

from .abstract_molecule_adapter import AbstractMoleculeAdapter


# Disable the Open Babel logging. Unfortunately, we cannot redirect the stream
# which would be preferable.
ob.obErrorLog.SetOutputLevel(-1)


logger = logging.getLogger(__name__)


class OpenBabelMoleculeAdapter(AbstractMoleculeAdapter):
    """
    Define the Open Babel molecule adapter.

    An adapter to a molecule class that can be instantiatied either using Open Babel,
    RDKit, or ChemAxon.

    """

    def __init__(self, *, molecule: pybel.Molecule, **kwargs):
        """"""
        super().__init__(molecule=molecule, **kwargs)

    @classmethod
    def from_mol_block(cls, mol: str) -> Optional[OpenBabelMoleculeAdapter]:
        """Return an OpenBabelMoleculeAdapter instance from an MDL MOL block."""
        try:
            return OpenBabelMoleculeAdapter(molecule=pybel.readstring("mol", mol))
        except IOError as error:
            logger.error(
                "Failed to generate an Open Babel molecule from MDL MOL block."
            )
            logger.debug(mol, exc_info=error)
            return

    @classmethod
    def from_inchi(cls, inchi: str) -> Optional[OpenBabelMoleculeAdapter]:
        """Return an OpenBabelMoleculeAdapter instance from an InChI string."""
        try:
            return OpenBabelMoleculeAdapter(molecule=pybel.readstring("inchi", inchi))
        except IOError as error:
            logger.error("Failed to generate an Open Babel molecule from InChI.")
            logger.debug(inchi, exc_info=error)
            return

    @classmethod
    def from_smiles(cls, smiles: str) -> Optional[OpenBabelMoleculeAdapter]:
        """Return an OpenBabelMoleculeAdapter instance from a SMILES string."""
        try:
            return OpenBabelMoleculeAdapter(molecule=pybel.readstring("smiles", smiles))
        except IOError as error:
            logger.error("Failed to generate an Open Babel molecule from SMILES.")
            logger.debug(smiles, exc_info=error)
            return

    def get_inchi(self) -> str:
        """Return an InChI representation of the molecule."""
        return self._molecule.write("inchi").strip()

    def get_inchi_key(self) -> str:
        """Return an InChIKey representation of the molecule."""
        return self._molecule.write("inchikey").strip()

    def get_smiles(self) -> str:
        """Return a SMILES representation of the molecule."""
        return self._molecule.write("smiles").strip()

    def get_chemical_formula(self) -> str:
        """Return a chemical formula of the molecule."""
        return self._molecule.formula

    def get_molecular_mass(self) -> float:
        """Return the molecular mass of the molecule in dalton (Da or u)."""
        # TODO: Make sure this is in dalton and not g/mol.
        return self._molecule.molwt

    def get_charge(self) -> int:
        """Return the molecule's formal charge."""
        return self._molecule.charge
