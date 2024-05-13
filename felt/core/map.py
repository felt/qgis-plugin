"""
Felt API Map
"""

import json
from dataclasses import dataclass
from typing import (
    Optional,
    Union,
    Dict
)

from qgis.PyQt.QtCore import (
    Qt,
    QDateTime
)

from .enums import ObjectType


@dataclass
class Map:
    """
    Represents a map
    """

    url: Optional[str]
    id: Optional[str]
    title: Optional[str]
    type: Optional[ObjectType]
    thumbnail_url: Optional[str]
    last_visited: Optional[QDateTime]

    @staticmethod
    def from_json(jsons: Union[str, Dict]) -> 'Map':
        """
        Creates a map from a JSON string
        """
        if isinstance(jsons, str):
            res = json.loads(jsons)
        else:
            res = jsons

        if res.get('data'):
            res = res['data']

        last_visited_string = res.get('attributes', {}).get('visited_at')
        if last_visited_string:
            last_visited = QDateTime.fromString(
                last_visited_string, Qt.ISODate
            )
        else:
            last_visited = None

        return Map(
            url=res.get('attributes', {}).get('url'),
            id=res.get('id'),
            title=res.get('attributes', {}).get('title'),
            type=ObjectType.from_string(res.get('type')),
            thumbnail_url=res.get('attributes', {}).get('thumbnail_url'),
            last_visited=last_visited
        )
