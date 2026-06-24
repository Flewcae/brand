from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class PublicURLS3Boto3Storage(S3Boto3Storage):
    """Identical to S3Boto3Storage except returned URLs point at
    AWS_S3_PUBLIC_ENDPOINT_URL instead of AWS_S3_ENDPOINT_URL.

    Django talks to MinIO over the Docker-internal hostname (`minio:9000`),
    but browsers resolving that same URL can't -- they need the
    host-published address (`localhost:9000` in dev, a real public
    endpoint in prod). Safe to rewrite post-signing: MinIO's query-string
    auth here is SigV2, whose signature does not cover the Host header
    (verified empirically), so changing the host after signing does not
    invalidate the signature.
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        url = super().url(name, parameters=parameters, expire=expire, http_method=http_method)
        if settings.AWS_S3_PUBLIC_ENDPOINT_URL and settings.AWS_S3_ENDPOINT_URL:
            url = url.replace(settings.AWS_S3_ENDPOINT_URL, settings.AWS_S3_PUBLIC_ENDPOINT_URL, 1)
        return url
