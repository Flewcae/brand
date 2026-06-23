from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Agency, AgencyMembership, User


class RegisterAndAuthTests(APITestCase):
    def test_register_creates_user_agency_and_membership(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "founder@example.com", "password": "strongpass123", "agency_name": "Acme"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="founder@example.com")
        agency = Agency.objects.get(name="Acme")
        self.assertTrue(AgencyMembership.objects.filter(agency=agency, user=user).exists())

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@example.com", password="x")
        response = self.client.post(
            "/api/auth/register/",
            {"email": "dup@example.com", "password": "strongpass123", "agency_name": "Acme"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_obtain_with_email(self):
        User.objects.create_user(email="login@example.com", password="strongpass123")
        response = self.client.post(
            "/api/auth/token/",
            {"email": "login@example.com", "password": "strongpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class AgencyMembershipTests(APITestCase):
    def test_unique_membership_constraint(self):
        user = User.objects.create_user(email="member@example.com", password="x")
        agency = Agency.objects.create(name="Acme")
        AgencyMembership.objects.create(agency=agency, user=user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AgencyMembership.objects.create(agency=agency, user=user)

    def test_my_agency_endpoint_scoped_to_membership(self):
        user = User.objects.create_user(email="member2@example.com", password="x")
        agency = Agency.objects.create(name="Acme2")
        AgencyMembership.objects.create(agency=agency, user=user)
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/agencies/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(agency.id))

    def test_unauthenticated_request_rejected(self):
        response = self.client.get("/api/agencies/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_member_deactivates_not_deletes(self):
        owner = User.objects.create_user(email="owner@example.com", password="x")
        other = User.objects.create_user(email="other@example.com", password="x")
        agency = Agency.objects.create(name="Acme3")
        AgencyMembership.objects.create(agency=agency, user=owner)
        membership = AgencyMembership.objects.create(agency=agency, user=other)

        self.client.force_authenticate(user=owner)
        response = self.client.delete(f"/api/agencies/{agency.id}/members/{membership.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
