"""
Felt API Workspace
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
