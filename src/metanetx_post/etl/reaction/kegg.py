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


"""Extract, transform, and load KEGG reaction information."""


from io import StringIO
from typing import Any, Coroutine, Optional, Set

import httpx
import pyparsing as pp


__all__ = ("fetch_kegg_reaction_list", "reaction_fetcher", "KEGGReactionNameParser")


async def fetch_kegg_reaction_list(
    url: str = "http://rest.kegg.jp/list/reaction",
) -> StringIO:
    """"""
    text = StringIO()
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            async for chunk in response.aiter_text():
                text.write(chunk)
    # We set cursor to beginning such that the buffer can be read like a file.
    text.seek(0)
    return text


def reaction_fetcher(
    identifier: str, client: httpx.AsyncClient
) -> Coroutine[Any, Any, httpx.Response]:
    """
    Prepare an asynchronous HTTP call to retrieve a KEGG reaction description.

    Parameters
    ----------
    identifier : str
        The KEGG reaction identifier.
    client : httpx.AsyncClient
        An httpx asynchronous client with a `base_url` set.

    Returns
    -------
    coroutine
        A `client.get` call that can be awaited by the caller of this function.

    """
    return client.get(identifier)


class KEGGReactionNameParser:

    pp.ParserElement.setDefaultWhitespaceChars(" \t")

    name = pp.Word(pp.printables, excludeChars=";")
    name.setName("name")

    reaction_names = (
        pp.LineStart()
        + pp.Keyword("NAME")
        + pp.Group(pp.delimitedList(pp.Group(name[1, ...])("name"), delim=";"))("names")
        + pp.LineEnd()
    )
    reaction_names.setName("reaction_names")

    @classmethod
    def parse(cls, block: str) -> Optional[Set[str]]:
        """
        Parse all names from a KEGG reaction description.

        Parameters
        ----------
        block : str
            A KEGG reaction description in their flat file format.

        Returns
        -------
        list
            A list of names found in the description.

        Raises
        ------
        AssertionError
            If more than one NAME line is found.

        """
        result = cls.reaction_names.searchString(block)
        assert len(result) <= 1, block
        if len(result) == 0:
            return
        return {" ".join(n) for n in result[0].names}
