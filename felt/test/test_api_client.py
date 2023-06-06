# coding=utf-8
"""Felt API client Test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = '(C) 2022 by Nyall Dawson'
__date__ = '23/11/2022'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import unittest

from .utilities import get_qgis_app
from qgis.PyQt.QtCore import (
    QUrl,
    QUrlQuery
)
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
    QNetworkReply
)
from qgis.PyQt.QtTest import QSignalSpy

from ..core import (
    OAuthWorkflow,
    UserType,
    FeltApiClient,
    User
)


QGIS_APP = get_qgis_app()


class ApiClientTest(unittest.TestCase):
    """Test API client work."""

    @classmethod
    def setUpClass(cls):
        workflow = OAuthWorkflow()
        workflow_finished = QSignalSpy(workflow.finished)
        workflow.start()
        workflow_finished.wait()

        cls.client = FeltApiClient()
        cls.client.set_token(workflow_finished[0][0])

    def test_build_url(self):
        """
        Test building urls
        """
        self.assertEqual(
            FeltApiClient.build_url('/user'),
            QUrl('https://felt.com/api/v1/user')
        )

    def test_to_url_query(self):
        """
        Test converting dictionaries to url queries
        """
        res = FeltApiClient._to_url_query({})
        self.assertIsInstance(res, QUrlQuery)
        self.assertTrue(res.isEmpty())

        res = FeltApiClient._to_url_query({'a': 'b',
                                           'c': 'd'})
        self.assertIsInstance(res, QUrlQuery)
        self.assertFalse(res.isEmpty())
        self.assertTrue(res.hasQueryItem('a'))
        self.assertEqual(res.queryItemValue('a'), 'b')
        self.assertTrue(res.hasQueryItem('c'))
        self.assertEqual(res.queryItemValue('c'), 'd')
        self.assertEqual(res.toString(), 'a=b&c=d')

    def test_build_request(self):
        """
        Test building network requests
        """
        res = FeltApiClient()._build_request('/test')
        self.assertIsInstance(res, QNetworkRequest)
        self.assertEqual(res.url().toString(), 'https://felt.com/api/v1/test')
        self.assertTrue(res.hasRawHeader(b'accept'))
        self.assertEqual(res.rawHeader(b'accept'), b'application/json')

        # with extra headers
        res = FeltApiClient()._build_request('/test',
                                             {'custom': 'custom_header'})
        self.assertIsInstance(res, QNetworkRequest)
        self.assertEqual(res.url().toString(), 'https://felt.com/api/v1/test')
        self.assertTrue(res.hasRawHeader(b'accept'))
        self.assertEqual(res.rawHeader(b'accept'), b'application/json')
        self.assertTrue(res.hasRawHeader(b'custom'))
        self.assertEqual(res.rawHeader(b'custom'), b'custom_header')

        # with query
        res = FeltApiClient()._build_request('/test', params={'a': 'b'})
        self.assertIsInstance(res, QNetworkRequest)
        self.assertEqual(res.url().toString(),
                         'https://felt.com/api/v1/test?a=b')
        self.assertTrue(res.hasRawHeader(b'accept'))
        self.assertEqual(res.rawHeader(b'accept'), b'application/json')

    def test_user(self):
        """
        Test user endpoint
        """
        # an unauthenticated client
        reply = FeltApiClient().user()
        spy = QSignalSpy(reply.finished)
        self.assertIsInstance(reply, QNetworkReply)
        self.assertEqual(reply.request().url().toString(),
                         'https://felt.com/api/v1/user')

        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.AuthenticationRequiredError)

        # an authenticated client
        reply = ApiClientTest.client.user()
        spy = QSignalSpy(reply.finished)
        self.assertIsInstance(reply, QNetworkReply)
        self.assertEqual(reply.request().url().toString(),
                         'https://felt.com/api/v1/user')

        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NoError)

        user = User.from_json(reply.readAll().data().decode())
        self.assertEqual(user.name, 'Nyall Dawson')
        self.assertEqual(user.email, 'nyall.dawson@gmail.com')
        self.assertEqual(user.type, UserType.User)
        self.assertEqual(user.id, '7be58c2c-89b9-483d-aa04-d79cf97a2021')


if __name__ == "__main__":
    suite = unittest.makeSuite(ApiClientTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
