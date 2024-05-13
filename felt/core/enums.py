"""
Enums
"""

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
        """
        Converts string value to an object type
        """
        return {
            'user': ObjectType.User,
            'map': ObjectType.Map
        }[string]


class AuthState(Enum):
    """
    Authentication states
    """
    NotAuthorized = auto()
    Authorizing = auto()
    Authorized = auto()


class LayerExportResult(Enum):
    """
    Results of exporting a layer
    """
    Success = auto()
    Canceled = auto()


class LayerSupport(Enum):
    """
    Reasons why a layer is not supported
    """
    Supported = auto()
    NotImplementedProvider = auto()
    NotImplementedLayerType = auto()
    EmptyLayer = auto()
    UnsavedEdits = auto()

    def should_report(self) -> bool:
        """
        Returns True if the layer support should be reported to Felt
        usage API
        """
        return self not in (
            LayerSupport.Supported,
            LayerSupport.EmptyLayer
        )

    def should_prevent_sharing_maps(self) -> bool:
        """
        Returns True if the layer support should completely block sharing
        maps
        """
        return self in (
            LayerSupport.UnsavedEdits,
        )


class UsageType(Enum):
    """
    Usage types for reporting plugin usage
    """
    Error = auto()
    Info = auto()

    @staticmethod
    def from_string(string: str) -> 'UsageType':
        """
        Returns a UsageType from a string value
        """
        return {
            'error': UsageType.Error,
            'info': UsageType.Info
        }[string]

    def to_string(self) -> str:
        """
        Converts usage type to a string for API usage
        """
        return {
            UsageType.Error: 'error',
            UsageType.Info: 'info'
        }[self]
