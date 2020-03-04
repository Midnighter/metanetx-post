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

import rdkit.Chem as chem
from rdkit.Chem import Descriptors, rdMolDescriptors, rdmolops
from rdkit.Chem.inchi import InchiReadWriteError

from .abstract_molecule_adapter import AbstractMoleculeAdapter


logger = logging.getLogger(__name__)


class RDKitMoleculeAdapter(AbstractMoleculeAdapter):
    """Define the RDKit molecule adapter."""

    def __init__(self, *, molecule: chem.rdkit.Mol, **kwargs):
        """"""
        super().__init__(molecule=molecule, **kwargs)

    @classmethod
    def from_mol_block(cls, mol: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from an MDL MOL block."""
        molecule = chem.MolFromMolBlock(mol)
        if molecule:
            return RDKitMoleculeAdapter(molecule=molecule)
        else:
            logger.error("Failed to generate an RDKit molecule from MDL MOL block.")
            return

    @classmethod
    def from_inchi(cls, inchi: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from an InChI string."""
        molecule = chem.MolFromInchi(inchi)
        if molecule:
            return RDKitMoleculeAdapter(molecule=molecule)
        else:
            logger.error("Failed to generate an RDKit molecule from InChI.")
            return

    @classmethod
    def from_smiles(cls, smiles: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from a SMILES string."""
        molecule = chem.MolFromSmiles(smiles)
        if molecule:
            return RDKitMoleculeAdapter(molecule=molecule)
        else:
            logger.error("Failed to generate an RDKit molecule from SMILES.")
            return

    def get_inchi(self) -> str:
        """Return an InChI representation of the molecule."""
        return chem.MolToInchi(self._molecule)

    def get_inchi_key(self) -> str:
        """Return an InChIKey representation of the molecule."""
        return chem.MolToInchiKey(self._molecule)

    def get_smiles(self) -> str:
        """Return a SMILES representation of the molecule."""
        return chem.MolToSmiles(self._molecule)

    def get_chemical_formula(self) -> str:
        """Return a chemical formula of the molecule."""
        return rdMolDescriptors.CalcMolFormula(self._molecule)

    def get_molecular_mass(self) -> float:
        """
        Return the molecular mass of the molecule in dalton (Da or u).

        This takes into account the average atom mass based on isotope frequency.
        """
        return Descriptors.MolWt(self._molecule)

    def get_charge(self) -> int:
        """Return the molecule's formal charge."""
        return rdmolops.GetFormalCharge(self._molecule)
