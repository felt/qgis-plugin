"""
Felt API s3 upload parameters
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class S3UploadParameters:
    """
    Encapsulates parameters for uploading to S3, including all presigned
    attributes
    """

    url: str
    layer_id: str
    type: str
    _presigned_attributes: Dict[str, str]

    def to_form_fields(self) -> Dict:
        """
        Returns all form fields including the presigned attributes required
        for the upload
        """
        return {**self._presigned_attributes}

    @staticmethod
    def from_json(res: Dict[str, str]) -> 'S3UploadParameters':
        """
        Creates upload parameters from a JSON response, capturing all
        presigned attributes
        """
        return S3UploadParameters(
            url=res.get('url'),
            layer_id=res.get('layer_id'),
            type=res.get('data', {}).get('type'),
            _presigned_attributes=res.get('presigned_attributes', {})
        )
