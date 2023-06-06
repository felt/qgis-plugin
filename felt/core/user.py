# -*- coding: utf-8 -*-
"""Felt API User

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
    Optional
)

from .enums import UserType


@dataclass
class User:
    """
    Represents a user
    """

    name: Optional[str]
    email: Optional[str]
    id: Optional[str]
    type: Optional[UserType]

    @staticmethod
    def from_json(jsons: str) -> 'User':
        """
        Creates a user from a JSON string
        """
        res = json.loads(jsons)
        return User(
            name=res.get('data', {}).get('attributes', {}).get('name'),
            email=res.get('data', {}).get('attributes', {}).get('email'),
            id=res.get('data', {}).get('id'),
            type=UserType.from_string(res.get('data', {}).get('type')),
        )
