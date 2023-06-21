# -*- coding: utf-8 -*-
"""Felt API client

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

import configparser
import re
from pathlib import Path
from typing import Tuple


class PluginMetadataParser:
    """
    Plugin metadata parser
    """

    #: Semantic version regex
    VERSION_REGEX = re.compile(r'^(\d+)\.(\d+).*')

    def __init__(self):
        self._meta_parser = configparser.ConfigParser()
        self._meta_parser.read(
            str(Path(__file__).parent.parent / 'metadata.txt')
        )
        self._prop_cache = {}

    @staticmethod
    def semantic_version(version: str) -> Tuple[int, int]:
        """
        Converts a version string to a (major, minor) version tuple.
        """
        m = PluginMetadataParser.VERSION_REGEX.match(version)
        if not m or len(m.groups()) != 2:
            return 0, 0
        return tuple(int(v) for v in m.groups())  # noqa

    def get_property(self, name, section='general'):
        """
        Reads the property with the given name from the local plugin metadata.
        """
        key = f'{section}.{name}'
        try:
            value = self._prop_cache.get(
                key,
                self._meta_parser.get(section, name)
            )
        except (configparser.NoOptionError, configparser.NoSectionError):
            value = None
        self._prop_cache[key] = value
        return value

    def get_app_name(self) -> str:
        """
        Returns the name of the QGIS plugin.
        """
        return self.get_property("name")

    def get_long_app_name(self) -> str:
        """
        Returns the full name of the QGIS plugin.
        Depending on the settings, this may return the same as calling
        get_app_name().
        """
        long_name = self.get_property("longName")
        if long_name:
            return long_name
        return self.get_app_name()

    def get_short_app_name(self) -> str:
        """ Returns the short name of the QGIS plugin.
        Depending on the settings, this may return the same as
        calling get_app_name().
        """
        short_name = self.get_property("shortName")
        if short_name:
            return short_name
        return self.get_app_name()

    def get_tracker_url(self) -> str:
        """
        Returns the issue tracker URL for the plugin.
        """
        return self.get_property("tracker")

    def get_version(self) -> str:
        """
        Returns the plugin version string.
        """
        return self.get_property("version").strip()

    def get_docs_url(self) -> str:
        """
        Returns the plugin documentation URL.
        """
        return self.get_property("docs", "bridge").rstrip('/')


PLUGIN_METADATA_PARSER = PluginMetadataParser()
