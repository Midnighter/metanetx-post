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


import asyncio
import logging
import time
from io import StringIO
from math import ceil
from typing import Any, Callable, Collection, Coroutine, Tuple

import httpx
from pandas import DataFrame
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm


__all__ = (
    "fetch_kegg_list",
    "fetch_kegg_resources",
)


logger = logging.getLogger(__name__)


Session = sessionmaker()


async def fetch_kegg_list(
    database: str, url: str = "http://rest.kegg.jp/list",
) -> StringIO:
    """Fetch the tabular overview of a KEGG database."""
    text = StringIO()
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", f"{url}/{database}") as response:
            async for chunk in response.aiter_text():
                text.write(chunk)
    # We set cursor to beginning such that the buffer can be read like a file.
    text.seek(0)
    return text


async def fetch_kegg_resources(
    identifiers: Collection[str],
    fetcher: Callable[[str, httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]],
    url: str = "http://rest.kegg.jp/get/",
    requests_per_second: int = 10,
) -> DataFrame:
    """
    Fetch large amounts of resources from the KEGG REST API.

    The resources are specified via their corresponding identifier and a specific
    callable that further details the resource.

    Parameters
    ----------
    identifiers : collection of str
        The KEGG identifiers to fetch resources for.
    fetcher : callable
        Called with a single KEGG identifier and an httpx.AsyncClient instance that
        contains the `url` as a basis. Expected to return a coroutine from which to
        await the response.
    url : str, optional
        The base URL for the KEGG REST API.
    requests_per_second : int, optional
        The desired requests per second to make. The default of 10 is the desired limit
        by KEGG.

    Returns
    -------
    pandas.DataFrame
        A data frame with three columns where each row corresponds to one identifier,
        the HTTP response status code, and the response body.

    See Also
    --------
    etl.kegg_mol_fetcher
    etl.kegg_reaction_fetcher

    """
    identifiers = list(identifiers)
    # The design decision is that the go event should be active most of the time and
    # only inactivated if we need to back off from making requests to the API.
    go_event = asyncio.Event()
    go_event.set()
    # We create a lock so that multiple requests hitting a rate-limit can be
    # coordinated and the number of requests per second throttled correctly.
    request_lock = asyncio.Lock()
    results = []
    with tqdm(total=len(identifiers), desc="Fetch Resource") as pbar:
        async with httpx.AsyncClient(
            base_url=url,
            pool_limits=httpx.PoolLimits(hard_limit=requests_per_second),
            timeout=httpx.Timeout(pool_timeout=None),
        ) as client:
            while len(identifiers) > 0:
                tasks = identifiers[-requests_per_second:]
                del identifiers[-requests_per_second:]
                start = time.perf_counter()
                results.extend(
                    await asyncio.gather(
                        *[
                            fetch_resource(i, client, fetcher, go_event, request_lock)
                            for i in tasks
                        ]
                    )
                )
                delta = time.perf_counter() - start
                # We keep our number of requests per second conservative by always
                # waiting until the next second window.
                await asyncio.sleep(ceil(delta) - delta)
                pbar.update(len(tasks))
    return DataFrame(data=results, columns=["identifier", "status_code", "response"])


async def fetch_resource(
    identifier: str,
    client: httpx.AsyncClient,
    fetcher: Callable[[str, httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]],
    go_event: asyncio.Event,
    request_lock: asyncio.Lock,
    base_wait_time: int = 1,
    exponential_factor: int = 2,
    max_attempts: int = 10,
) -> Tuple[str, int, str]:
    """
    Fetch a single mol description of a compound from KEGG and convert it to InChI.

    Parameters
    ----------
    identifier : str
        The resource identifier.
    client : httpx.AsyncClient
        An httpx asynchronous client with a `base_url` set.
    fetcher : callable
        A coroutine that combines the client and the given identifier for the
        specific resource.
    go_event : asyncio.Event
    request_lock : asyncio.Lock
    base_wait_time : int
    exponential_factor : int
    max_attempts : int, optional

    Returns
    -------
    tuple
        A triple of the resource identifier, the HTTP response code, and optionally
        the response body as text.

    """
    # If the go event is cleared, i.e., we need to back off, this will halt
    # making a request until we are good to go again.
    await go_event.wait()
    response = await fetcher(identifier, client)
    if response.status_code == 403:
        # Clear the event so that no more requests are submitted.
        go_event.clear()
        logger.warning(f"{identifier}: Hit API rate limit.")
        if request_lock.locked():
            # Some other coroutine is currently handling the backing off. We wait for
            # the event to go ahead.
            await go_event.wait()
            response = await fetcher(identifier, client)
        else:
            async with request_lock:
                # Introduce exponential backing off.
                wait_time = base_wait_time
                for attempt in range(max_attempts):
                    logger.info(f"{identifier}: Trying again in {wait_time} seconds.")
                    await asyncio.sleep(wait_time)
                    response = await fetcher(identifier, client)
                    if response.status_code != 403:
                        # We are cleared and good to continue.
                        go_event.set()
                        break
                    wait_time *= exponential_factor
                if (attempt + 1) >= max_attempts:
                    raise RuntimeError(
                        "Maximum number of back-off and retry attempts reached. Aborting."
                    )
    return identifier, response.status_code, response.text
