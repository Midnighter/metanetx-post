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


"""Provide BiGG data models."""


from datetime import datetime
from typing import List, Optional

import pydantic
from pydantic import BaseModel, Field


__all__ = ("BiGGSimpleReaction", "BiGGVersionModel", "BiGGUniversalReactionResult")


class BiGGVersionModel(BaseModel):
    """Define a data model that represents the BiGG database version."""

    bigg_models_version: pydantic.constr(regex=r"\d+\.\d+\.\d+") = Field(...)
    api_version: str = Field(...)
    last_updated: datetime = Field(...)


class BiGGSimpleReaction(BaseModel):
    """Define a data model for a simple BiGG reaction with a name."""

    bigg_id: str = Field(...)
    name: Optional[str] = Field(None)


class BiGGUniversalReactionResult(BaseModel):
    """Define a data model for universal reaction query results."""

    results: List[BiGGSimpleReaction] = Field(...)
    results_count: int = Field(...)
