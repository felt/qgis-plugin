# -*- coding: utf-8 -*-
"""Felt API s3 upload parameters

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

from dataclasses import dataclass
from typing import (
    Optional,
    Dict
)


@dataclass
class S3UploadParameters:
    """
    Encapsulates parameters for uploading to S3
    """

    aws_access_key_id: Optional[str]
    acl: Optional[str]
    key: Optional[str]
    policy: Optional[str]
    signature: Optional[str]
    success_action_status: Optional[str]
    x_amz_meta_features_flags: Optional[str]
    x_amz_meta_file_count: Optional[str]
    x_amz_security_token: Optional[str]
    url: Optional[str]
    layer_id: Optional[str]
    type: Optional[str]

    def to_form_fields(self) -> Dict:
        """
        Returns the form fields required for the upload
        """
        return {
            'AWSAccessKeyId': self.aws_access_key_id,
            'key': self.key,
            'policy': self.policy,
            'signature': self.signature,
            'success_action_status': self.success_action_status,
            'x-amz-meta-feature-flags': self.x_amz_meta_features_flags,
            'x-amz-meta-file-count': self.x_amz_meta_file_count,
            'x-amz-security-token': self.x_amz_security_token,
        }

    @staticmethod
    def from_json(res: str) -> 'S3UploadParameters':
        """
        Creates upload parameters from a JSON string
        """
        return S3UploadParameters(
            type=res.get('data', {}).get('type'),
            aws_access_key_id=res.get('data', {}).get('attributes', {}).get(
                'presigned_attributes', {}).get('AWSAccessKeyId'),
            acl=res.get('data', {}).get('attributes', {}).get(
                'presigned_attributes', {}).get('acl'),
            key=res.get('data', {}).get('attributes', {}).get(
                'presigned_attributes', {}).get('key'),
            policy=res.get('data', {}).get('attributes', {}).get(
                'presigned_attributes', {}).get('policy'),
            signature=res.get('data', {}).get('attributes', {}).get(
                'presigned_attributes', {}).get('signature'),
            success_action_status=res.get('data', {}).get('attributes',
                                                          {}).get(
                'presigned_attributes', {}).get('success_action_status'),
            x_amz_meta_features_flags=res.get('data', {}).get('attributes',
                                                              {}).get(
                'presigned_attributes', {}).get('x-amz-meta-feature-flags'),
            x_amz_meta_file_count=res.get('data', {}).get('attributes',
                                                          {}).get(
                'presigned_attributes', {}).get('x-amz-meta-file-count'),
            x_amz_security_token=res.get('data', {}).get('attributes',
                                                         {}).get(
                'presigned_attributes', {}).get('x-amz-security-token'),
            url=res.get('data', {}).get('attributes', {}).get('url'),
            layer_id=res.get('data', {}).get('attributes', {}).get('layer_id'),
        )
