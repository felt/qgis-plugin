"""
Felt API User
"""

import json
from dataclasses import dataclass
from typing import (
    Optional
)

from .enums import ObjectType


@dataclass
class User:
    """
    Represents a user
    """

    name: Optional[str]
    email: Optional[str]
    id: Optional[str]
    type: Optional[ObjectType]

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
            type=ObjectType.from_string(res.get('data', {}).get('type')),
        )
