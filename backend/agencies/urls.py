from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("agencies/me/", views.MyAgencyView.as_view(), name="agency-me"),
    path(
        "agencies/<uuid:agency_id>/members/",
        views.AgencyMembersView.as_view(),
        name="agency-members",
    ),
    path(
        "agencies/<uuid:agency_id>/members/invite/",
        views.InviteMemberView.as_view(),
        name="agency-member-invite",
    ),
    path(
        "agencies/<uuid:agency_id>/members/<uuid:membership_id>/",
        views.RemoveMemberView.as_view(),
        name="agency-member-remove",
    ),
]
