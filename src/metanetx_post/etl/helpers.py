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
from typing import Any, Callable, Collection, Coroutine, Optional, Tuple

import httpx
from pandas import DataFrame
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm


__all__ = ("fetch_resources",)


logger = logging.getLogger(__name__)

_REQUESTS_PER_SECOND = 0


Session = sessionmaker()


async def fetch_resources(
    identifiers: Collection[str],
    url: str,
    fetcher: Callable[[str, httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]],
    requests_per_second: int = 10,
) -> DataFrame:
    """

    Parameters
    ----------
    identifiers
    url
    fetcher
    requests_per_second

    Returns
    -------

    """
    global _REQUESTS_PER_SECOND
    _REQUESTS_PER_SECOND = requests_per_second
    tasks = []
    # The design decision is that the go event should be active most of the time and
    # only inactivated if we need to back off from making requests to the API.
    go_event = asyncio.Event()
    go_event.set()
    # We create a lock so that multiple requests hitting a rate-limit can be
    # coordinated and the number of requests per second throttled correctly.
    request_lock = asyncio.Lock()
    async with httpx.AsyncClient(
        base_url=url, pool_limits=httpx.PoolLimits(hard_limit=_REQUESTS_PER_SECOND),
    ) as client:
        for identifier in tqdm(
            identifiers, total=len(identifiers), desc="Submit " "Request"
        ):
            # If the go event is cleared, i.e., we need to back off, this will halt
            # submitting new requests until we are good to go again.
            await go_event.wait()
            tasks.append(
                asyncio.create_task(
                    fetch_resource(identifier, client, fetcher, go_event, request_lock)
                )
            )
            await asyncio.sleep(1 / _REQUESTS_PER_SECOND)
    results = [
        await future
        for future in tqdm(
            asyncio.as_completed(tasks), total=len(tasks), desc="Collect Response"
        )
    ]
    return DataFrame(data=results, columns=["identifier", "status_code", "response"])


async def fetch_resource(
    identifier: str,
    client: httpx.AsyncClient,
    fetcher: Callable[[str, httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]],
    go_event: asyncio.Event,
    request_lock: asyncio.Lock,
    max_attempts: int = 10,
) -> Tuple[str, int, Optional[str]]:
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
    max_attempts : int, optional

    Returns
    -------
    tuple
        A triple of the resource identifier, the HTTP response code, and optionally
        the response body as text.

    """
    global _REQUESTS_PER_SECOND
    # If the go event is cleared, i.e., we need to back off, this will halt
    # making a request until we are good to go again.
    await go_event.wait()
    response = await fetcher(identifier, client)
    if response.status_code == 403:
        # Clear the event so that no more requests are submitted.
        go_event.clear()
        logger.error(f"{identifier}: Hit API rate limit.")
        if request_lock.locked():
            # Some other coroutine is currently handling the backing off. We wait for
            # the event to go ahead.
            await go_event.wait()
            response = await fetcher(identifier, client)
        async with request_lock:
            # We reduce the number of requests made so that we don't hit the limit in
            # future.
            if _REQUESTS_PER_SECOND > 1:
                _REQUESTS_PER_SECOND -= 1
                logger.info(
                    f"Decreasing requests per second to {_REQUESTS_PER_SECOND}."
                )
            # Introduce exponential backing off.
            wait_time = 2
            for attempt in range(max_attempts):
                if response.status_code != 403:
                    # We are cleared and good to continue.
                    go_event.set()
                    break
                logger.info(f"{identifier}: Trying again in {wait_time} seconds.")
                await asyncio.sleep(wait_time)
                response = await fetcher(identifier, client)
                wait_time *= 2
            if (attempt + 1) >= max_attempts:
                raise RuntimeError(
                    "Maximum number of back-off and retry attempts reached. Aborting."
                )
    return identifier, response.status_code, response.text
