# -*- coding: utf-8 -*-
"""
Enums

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

from enum import (
    Enum,
    auto
)


class ObjectType(Enum):
    """
    Object types
    """
    User = auto()
    Map = auto()

    @staticmethod
    def from_string(string: str) -> 'ObjectType':
        return {
            'user': ObjectType.User,
            'map': ObjectType.Map
        }[string]


class AuthState(Enum):
    """
    Authentication states
    """
    LoggedOut = auto()
    LoggingIn = auto()
    LoggedIn = auto()
