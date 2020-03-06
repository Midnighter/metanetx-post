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


"""Provide a compound conflict data model."""


from typing import Dict, List

from cobra_component_models.io import CompoundModel
from pydantic import BaseModel


__all__ = ("InChIConflict", "InChIConflictReport")


class InChIConflict(BaseModel):
    """
    Define a data model that represents conflicts between different compounds by InChI.


    """

    candidate_compound: CompoundModel
    kegg_inchis: List[str]
    existing_compounds: List[CompoundModel]


class InChIConflictReport(BaseModel):
    """Define a collection of InChI-based compound conflicts."""

    conflicts: List[InChIConflict]
    duplicates: Dict[str, List[CompoundModel]]
