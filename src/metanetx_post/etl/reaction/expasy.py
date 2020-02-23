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


"""Extract, transform, and load ExPASy reaction information."""


from pathlib import Path, PurePosixPath
from typing import Dict, Set, Union
from urllib.parse import urlparse

import aioftp
import rdflib
from metanetx_sdk.model import PathInfoModel
from rdflib.namespace import SKOS
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm


__all__ = ("fetch_expasy_rdf", "collect_expasy_names", "collect_expasy_obsoletes")


Session = sessionmaker()


async def fetch_expasy_rdf(
    email: str,
    local_path: Path,
    host: str = "ftp.expasy.org",
    directory: PurePosixPath = PurePosixPath("databases/enzyme"),
    filename="enzyme.rdf",
    timeout: Union[float, int, None] = 5,
) -> None:
    """

    Parameters
    ----------
    email : str
        The email address to identify yourself with in the password field of your
        anonymous FTP connection. This is good etiquette but can be avoided by
        providing 'anon@'.
    local_path : pathlib.Path
        The local path where to store the downloaded file.
    host : str, optional
        The FTP server host URL.
    directory : pathlib.PurePosixPath, optional
        The directory on the FTP server where to find the desired file.
    filename : str, optional
        The desired file's name.
    timeout : float, int, or None, optional
         The desired timeout in seconds for FTP connections (default 5 s).

    """
    async with aioftp.ClientSession(
        host, password=email, socket_timeout=timeout, path_timeout=timeout
    ) as client:
        await client.change_directory(directory)
        info = PathInfoModel.parse_obj(await client.stat(filename))
        with local_path.open("wb") as handle, tqdm(
            total=info.size, desc="Bytes"
        ) as pbar:
            transferred = 0
            async with client.download_stream(filename) as stream:
                async for block in stream.iter_by_block():
                    handle.write(block)
                    transferred += len(block)
                    pbar.update(len(block))
            assert transferred == info.size, "Not all bytes were transferred."


def get_uri_basename(resource: str) -> str:
    """Return the 'basename' of a URI, i.e., the final path component."""
    parts = urlparse(resource)
    index = parts.path.rfind("/") + 1
    return parts.path[index:]


def collect_expasy_names(graph: rdflib.Graph) -> Dict[str, Set[str]]:
    """Return all EC-code names given by their preferred and alternative labels."""
    ec2name = {}
    for subject, object in graph.subject_objects(SKOS.prefLabel | SKOS.altLabel):
        ec_code = get_uri_basename(str(subject))
        ec2name.setdefault(ec_code, set()).add(str(object))
    return ec2name


def collect_expasy_obsoletes(graph: rdflib.Graph) -> Dict[str, str]:
    """Return a mapping from obsolete EC-codes to their replacements."""
    replaced_by = rdflib.URIRef("http://purl.uniprot.org/core/replacedBy")
    return {
        get_uri_basename(str(s)): get_uri_basename(str(o))
        for s, o in graph.subject_objects(replaced_by)
    }
