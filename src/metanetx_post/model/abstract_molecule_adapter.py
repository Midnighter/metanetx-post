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

from abc import ABC, abstractmethod
from typing import Any, Optional


__all__ = ("AbstractMoleculeAdapter",)


class AbstractMoleculeAdapter(ABC):
    """
    Define the abstract molecule adapter.

    An adapter to a molecule class that can be instantiatied either using Open Babel,
    RDKit, or ChemAxon.

    """

    def __init__(self, *, molecule: Any, **kwargs):
        """"""
        super().__init__(**kwargs)
        self._molecule = molecule

    @classmethod
    @abstractmethod
    def from_mol_block(cls, mol: str) -> Optional[AbstractMoleculeAdapter]:
        """Return an AbstractMoleculeAdapter instance from an MDL MOL block."""
        pass

    @classmethod
    @abstractmethod
    def from_inchi(cls, inchi: str) -> Optional[AbstractMoleculeAdapter]:
        """Return an AbstractMoleculeAdapter instance from an InChI string."""
        pass

    @classmethod
    @abstractmethod
    def from_smiles(cls, smiles: str) -> Optional[AbstractMoleculeAdapter]:
        """Return an AbstractMoleculeAdapter instance from a SMILES string."""
        pass

    @abstractmethod
    def get_inchi(self) -> str:
        """Return an InChI representation of the molecule."""
        pass

    @abstractmethod
    def get_inchi_key(self) -> str:
        """Return an InChIKey representation of the molecule."""
        pass

    @abstractmethod
    def get_smiles(self) -> str:
        """Return a SMILES representation of the molecule."""
        pass

    @abstractmethod
    def get_chemical_formula(self) -> str:
        """Return a chemical formula of the molecule."""
        pass

    @abstractmethod
    def get_molecular_mass(self) -> float:
        """Return the molecular mass of the molecule in dalton (Da or u)."""
        pass

    @abstractmethod
    def get_charge(self) -> int:
        """Return the molecule's formal charge."""
        pass
