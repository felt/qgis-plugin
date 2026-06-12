"""
Felt API client Test.
"""

import unittest
import json
from pathlib import Path

from qgis.PyQt.QtCore import (
    QUrl,
    QUrlQuery
)
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
    QNetworkReply
)
from qgis.PyQt.QtTest import QSignalSpy

from .utilities import get_qgis_app
from ..core import (
    # OAuthWorkflow,
    ObjectType,
    FeltApiClient,
    User,
    Map,
    S3UploadParameters
)

QGIS_APP = get_qgis_app()

TEST_DATA_PATH = Path(__file__).parent

CLIENT = FeltApiClient()


class ApiClientTest(unittest.TestCase):
    """Test API client work."""

    # pylint: disable=protected-access

    @classmethod
    def setUpClass(cls):
        # workflow = OAuthWorkflow()
        # workflow_finished = QSignalSpy(workflow.finished)
        # workflow.start()
        # workflow_finished.wait()

        # CLIENT.set_token(workflow_finished[0][0])
        pass

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

    @unittest.skipIf(not CLIENT.token, 'Not authorized')
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

        self.assertEqual(
            reply.error(),
            QNetworkReply.NetworkError.AuthenticationRequiredError)

        # an authenticated client
        reply = CLIENT.user()
        spy = QSignalSpy(reply.finished)
        self.assertIsInstance(reply, QNetworkReply)
        self.assertEqual(reply.request().url().toString(),
                         'https://felt.com/api/v1/user')

        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        user = User.from_json(reply.readAll().data().decode())
        self.assertEqual(user.name, 'Nyall Dawson')
        self.assertEqual(user.email, 'nyall.dawson@gmail.com')
        self.assertEqual(user.type, ObjectType.User)
        self.assertEqual(user.id, '7be58c2c-89b9-483d-aa04-d79cf97a2021')

    @unittest.skipIf(not CLIENT.token, 'Not authorized')
    def test_create_map(self):
        """
        Test create map
        """
        # an unauthenticated client
        reply = FeltApiClient().create_map(0, 0, 10)
        spy = QSignalSpy(reply.finished)
        self.assertIsInstance(reply, QNetworkReply)
        self.assertEqual(reply.request().url().toString(),
                         'https://felt.com/api/v1/maps')

        spy.wait()

        self.assertEqual(
            reply.error(),
            QNetworkReply.NetworkError.AuthenticationRequiredError)

        # an authenticated client
        reply = CLIENT.create_map(
            -24.962160, 153.311322, 10, title='Orchid Beach')
        spy = QSignalSpy(reply.finished)
        self.assertIsInstance(reply, QNetworkReply)
        self.assertEqual(reply.request().url().toString(),
                         'https://felt.com/api/v1/maps')

        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        created_map = Map.from_json(reply.readAll().data().decode())
        self.assertEqual(created_map.type, ObjectType.Map)
        self.assertTrue(created_map.url)
        self.assertTrue(created_map.id)

    @unittest.skipIf(not CLIENT.token, 'Not authorized')
    def test_create_layer(self):
        """
        Test create layer
        """
        reply = CLIENT.create_map(
            -24.962160, 153.311322, 10, title='Orchid Beach 22')
        spy = QSignalSpy(reply.finished)
        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        created_map = Map.from_json(reply.readAll().data().decode())

        self.assertEqual(created_map.type, ObjectType.Map)
        self.assertTrue(created_map.url)
        self.assertTrue(created_map.id)

        reply = CLIENT.prepare_layer_upload(
            created_map.id,
            'test_layer', ['test.gpkg']
        )
        spy = QSignalSpy(reply.finished)
        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        json_params = reply.readAll().data().decode()
        params = S3UploadParameters.from_json(json.loads(json_params))
        self.assertEqual(params.type, 'presigned_upload')
        self.assertTrue(params.aws_access_key_id, 'presigned_upload')
        # self.assertTrue(params.acl)
        self.assertTrue(params.key)
        self.assertTrue(params.policy)
        self.assertTrue(params.signature)
        self.assertEqual(params.success_action_status, '204')
        self.assertTrue(params.x_amz_meta_features_flags)
        self.assertEqual(params.x_amz_meta_file_count, '1')
        self.assertTrue(params.x_amz_security_token)
        self.assertTrue(params.url)
        self.assertTrue(params.layer_id)

        file = str(TEST_DATA_PATH / 'points.gpkg')

        with open(file, "rb") as f:
            data = f.read()

        reply = CLIENT.upload_file(
            'test.gpkg', data, params
        )
        spy = QSignalSpy(reply.finished)
        spy.wait()

        self.assertEqual(reply.error(), QNetworkReply.NetworkError.NoError)

        reply = CLIENT.finalize_layer_upload(
            created_map.id,
            params.layer_id,
            'test.gpkg'
        )
        spy = QSignalSpy(reply.finished)
        spy.wait()

        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        json_params = reply.readAll().data().decode()
        print(json_params)

    def test_create_upload_file_request(self):
        """
        Test building file upload requests (no network access required)
        """
        params = S3UploadParameters.from_json(
            {'url': 'https://test-bucket.s3.amazonaws.com/',
             'layer_id': 'layer_1',
             'data': {'type': 'presigned_upload'},
             'presigned_attributes': {
                 'key': 'some_key',
                 'policy': 'some_policy'
             }})

        request, form_content = CLIENT.create_upload_file_request(
            'test.gpkg', b'GPKG\x00\x01binary', params
        )

        self.assertEqual(request.url(),
                         QUrl('https://test-bucket.s3.amazonaws.com/'))
        self.assertEqual(request.rawHeader(b'Host'),
                         b'test-bucket.s3.amazonaws.com')

        body = bytes(form_content)
        self.assertIn(b'Content-Disposition: form-data; name="key"', body)
        self.assertIn(b'some_key\r\n', body)
        self.assertIn(b'Content-Disposition: form-data; name="policy"', body)
        self.assertIn(b'some_policy\r\n', body)
        self.assertIn(
            b'form-data; name="file"; filename="test.gpkg"', body)
        self.assertIn(b'GPKG\x00\x01binary', body)
        self.assertTrue(
            body.endswith(b'--QGISFormBoundary2XCkqVRLJ5XMxfw5--\r\n'))
        self.assertEqual(request.rawHeader(b'Content-Length'),
                         str(len(body)).encode())

    @unittest.skipIf(not CLIENT.token, 'Not authorized')
    def test_usage(self):
        """
        Test plugin usage api
        """
        reply = CLIENT.report_usage(
            'test'
        )
        spy = QSignalSpy(reply.finished)
        spy.wait()

        # reply should be empty response
        self.assertEqual(reply.error(),
                         QNetworkReply.NetworkError.NoError)

        self.assertFalse(reply.readAll())

    # pylint: enable=protected-access


if __name__ == "__main__":
    suite = unittest.makeSuite(ApiClientTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
