"""Felt API Workspace

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import json
from dataclasses import dataclass
from typing import (
    Optional,
    Union,
    Dict
)


@dataclass
class Workspace:
    """
    Represents a workspace
    """

    url: Optional[str]
    id: Optional[str]
    name: Optional[str]

    @staticmethod
    def from_json(jsons: Union[str, Dict]) -> 'Workspace':
        """
        Creates a workspace from a JSON string
        """
        if isinstance(jsons, str):
            res = json.loads(jsons)
        else:
            res = jsons

        return Workspace(
            url=res.get('attributes', {}).get('url'),
            id=res.get('id'),
            name=res.get('attributes', {}).get('name'),
        )
