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


"""Provide helper functions and values."""


__all__ = ("JSON_SEPARATORS", "convert2json_type")


JSON_SEPARATORS = (",", ":")


def convert2json_type(obj: set) -> list:
    """Convert sets to lists for JSON serialization."""
    if isinstance(obj, set):
        return list(obj)
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable.")
