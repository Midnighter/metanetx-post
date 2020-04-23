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


"""Populate compound information using PubChem."""


import logging
from typing import List, Tuple

import httpx
from cobra_component_models.orm import (
    BiologyQualifier,
    Compound,
    CompoundAnnotation,
    CompoundName,
    Namespace,
)
from metanetx_assets.model import IdentifiersOrgNamespaceModel
from sqlalchemy import exists
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from ...model import (
    PubChemCompoundModel,
    PubChemPropertyResponseModel,
    PubChemSynonymsResponseModel,
)


__all__ = ("extract", "transform", "load")


logger = logging.getLogger(__name__)


Session = sessionmaker()


def extract(
    identifiers: List[str], url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
) -> Tuple[str, str]:
    """
    Fetch compound information from PubChem.

    Parameters
    ----------
    identifiers: list
        A collection of PubChem compound identifiers.
    url : str, optional
        The URL to query for the PubChem compounds.

    Returns
    -------
    tuple
        The pair of properly encoded response strings for compound properties and
        synonyms.

    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"cid": ",".join(identifiers)}
    property_response = httpx.post(
        f"{url}/compound/cid/property/inchi,inchikey,iupacname/",
        headers=headers,
        data=data,
    )
    property_response.raise_for_status()
    synonyms_response = httpx.post(
        f"{url}/compound/cid/synonyms/", headers=headers, data=data,
    )
    synonyms_response.raise_for_status()
    return property_response.text, synonyms_response.text


def transform(
    property_response: str, synonyms_response: str
) -> List[PubChemCompoundModel]:
    """
    Transform the PubChem compound properties and synonyms into a mapping.

    Parameters
    ----------
    property_response : str
        The PubChem JSON response of requested compound properties.
    synonyms_response : str
        The PubChem JSON response of compound synonyms.

    Returns
    -------
    list
        A collection of PubChem compound objects.

    Raises
    ------
    pydantic.ValidationError
        In case the JSON response data has an unexpected format.
    AssertionError
        In case the compound properties and synonyms do not match.

    """
    properties = PubChemPropertyResponseModel.parse_raw(
        property_response
    ).property_table.properties
    synonyms = PubChemSynonymsResponseModel.parse_raw(
        synonyms_response
    ).information_list.information
    compounds = []
    # We expect compound properties and synonyms to be in the same order since the
    # identifiers are submitted in the same order.
    assert len(properties) == len(synonyms)
    for props, information in tqdm(
        zip(properties, synonyms), total=len(synonyms), desc="Compound"
    ):
        assert props.cid == information.cid
        # `construct` bypasses all pydantic validation. It is safe to use here because
        # we already validated the data before.
        compound = PubChemCompoundModel.construct(**props.dict())
        compound.synonyms = information.synonyms
        compounds.append(compound)
    return compounds


def load(
    session: Session,
    compounds: List[PubChemCompoundModel],
    url: str = "https://registry.api.identifiers.org/restApi/namespaces/search/findByPrefix",
) -> None:
    """
    Load PubChem compound objects into the database.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        An active session in order to communicate with a SQL database.
    compounds : list
        A collection of PubChem compound models.
    url : str, optional
        A URL to retrieve the PubChem namespace definition in case it does not exist
        yet.

    """
    # We either retrieve or create the PubChem compound namespace.
    pubchem_ns = (
        session.query(Namespace)
        .filter(Namespace.prefix == "pubchem.compound")
        .one_or_none()
    )
    if pubchem_ns is None:
        response = httpx.get(url, params={"prefix": "pubchem.compound"})
        response.raise_for_status()
        model = IdentifiersOrgNamespaceModel.parse_raw(response.text)
        pubchem_ns = Namespace(**model.dict())
        session.add(pubchem_ns)
        session.commit()
    bq_is = BiologyQualifier.get_map(session)["is"]
    for compound in tqdm(compounds, desc="Compound"):
        if session.query(exists().where(Compound.inchi == compound.inchi)).scalar():
            logger.warning(
                f"InChI for pubchem.compound:{compound.cid} already exists in the "
                f"database. Skipping."
            )
            logger.debug(compound.inchi)
            continue
        db_compound = Compound(inchi=compound.inchi, inchi_key=compound.inchi_key)
        db_compound.annotation.append(
            CompoundAnnotation(
                identifier=str(compound.cid),
                namespace=pubchem_ns,
                biology_qualifier=bq_is,
            )
        )
        db_compound.names.append(
            CompoundName(
                namespace=pubchem_ns, name=compound.iupac_name, is_preferred=True
            )
        )
        db_compound.names.extend(
            (CompoundName(namespace=pubchem_ns, name=n) for n in compound.synonyms)
        )
        session.add(db_compound)
        session.commit()
