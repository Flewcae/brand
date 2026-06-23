"""Shared test helpers used across app test suites -- not a Django app,
just a plain module importable because backend/ is on sys.path."""

from unittest.mock import MagicMock

from agencies.models import Agency, AgencyMembership, User
from brands.models import BrandProfile


def create_agency_with_user(email="user@example.com", password="testpass1234", agency_name="Test Agency"):
    user = User.objects.create_user(email=email, password=password)
    agency = Agency.objects.create(name=agency_name)
    AgencyMembership.objects.create(agency=agency, user=user)
    return user, agency


def create_brand(agency, **kwargs):
    defaults = dict(
        name="Test Brand",
        slug="test-brand",
        country_code="TR",
        timezone="Europe/Istanbul",
    )
    defaults.update(kwargs)
    return BrandProfile.objects.create(agency=agency, **defaults)


def make_claude_response(text, input_tokens=10, output_tokens=20):
    """Mimics an anthropic.types.Message response shape: .content is a list
    of blocks with .type/.text, .usage has input_tokens/output_tokens."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def make_httpx_response(json_data=None, content=b""):
    """Mimics an httpx.Response: .raise_for_status() no-ops, .json() and
    .content return the given fixtures."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = json_data if json_data is not None else {}
    response.content = content
    return response
