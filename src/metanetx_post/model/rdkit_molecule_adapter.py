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

from typing import Optional

import rdkit.Chem as chem
from rdkit.Chem import Descriptors, rdMolDescriptors, rdmolops

from .abstract_molecule_adapter import AbstractMoleculeAdapter


class RDKitMoleculeAdapter(AbstractMoleculeAdapter):
    """
    Define the Open Babel molecule adapter.

    An adapter to a molecule class that can be instantiatied either using Open Babel,
    RDKit, or ChemAxon.

    """

    def __init__(self, *, molecule: chem.rdkit.Mol, **kwargs):
        """"""
        super().__init__(molecule=molecule, **kwargs)

    @classmethod
    def from_mol_block(cls, mol: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from an MDL MOL block."""
        return RDKitMoleculeAdapter(molecule=chem.MolFromMolBlock(mol))

    @classmethod
    def from_inchi(cls, inchi: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from an InChI string."""
        return RDKitMoleculeAdapter(molecule=chem.MolFromInchi(inchi))

    @classmethod
    def from_smiles(cls, smiles: str) -> Optional[RDKitMoleculeAdapter]:
        """Return an RDKitMoleculeAdapter instance from a SMILES string."""
        return RDKitMoleculeAdapter(molecule=chem.MolFromSmiles(smiles))

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
