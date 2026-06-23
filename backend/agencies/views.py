from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Agency, AgencyMembership
from .serializers import (
    AgencyMembershipSerializer,
    AgencySerializer,
    InviteMemberSerializer,
    RegisterSerializer,
)


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "user": {"id": str(result["user"].id), "email": result["user"].email},
                "agency": AgencySerializer(result["agency"]).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyAgencyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        membership = (
            request.user.agency_memberships.filter(is_active=True)
            .select_related("agency")
            .first()
        )
        if not membership:
            return Response(
                {"detail": "Bu kullanıcı bir ajansa bağlı değil."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AgencySerializer(membership.agency).data)


def _user_belongs_to_agency(user, agency_id):
    return AgencyMembership.objects.filter(
        agency_id=agency_id, user=user, is_active=True
    ).exists()


class AgencyMembersView(generics.ListAPIView):
    serializer_class = AgencyMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        agency_id = self.kwargs["agency_id"]
        if not _user_belongs_to_agency(self.request.user, agency_id):
            return AgencyMembership.objects.none()
        return AgencyMembership.objects.filter(agency_id=agency_id).select_related("user")


class InviteMemberView(generics.GenericAPIView):
    serializer_class = InviteMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, agency_id):
        if not _user_belongs_to_agency(request.user, agency_id):
            return Response({"detail": "Ajans bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        agency = Agency.objects.get(id=agency_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership, created = AgencyMembership.objects.get_or_create(
            agency=agency, user=serializer.user, defaults={"is_active": True}
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=["is_active"])

        return Response(AgencyMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class RemoveMemberView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, agency_id, membership_id):
        if not _user_belongs_to_agency(request.user, agency_id):
            return Response({"detail": "Üyelik bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        membership = AgencyMembership.objects.filter(
            id=membership_id, agency_id=agency_id
        ).first()
        if not membership:
            return Response({"detail": "Üyelik bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
