# -*- coding: utf-8 -*-
"""Felt API Map

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2023 by Nyall Dawson'
__date__ = '1/06/2023'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import json
from dataclasses import dataclass
from typing import (
    Optional,
    Union,
    Dict
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

        return Map(
            url=res.get('attributes', {}).get('url'),
            id=res.get('id'),
            title=res.get('attributes', {}).get('title'),
            type=ObjectType.from_string(res.get('type')),
            thumbnail_url=res.get('thumbnail_url')
        )
