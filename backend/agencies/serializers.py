from django.db import transaction
from rest_framework import serializers

from .models import Agency, AgencyMembership, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class AgencyMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AgencyMembership
        fields = ["id", "user", "role", "is_active", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    agency_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu e-posta ile zaten bir hesap var.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        agency = Agency.objects.create(name=validated_data["agency_name"])
        AgencyMembership.objects.create(agency=agency, user=user)
        return {"user": user, "agency": agency}


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # MVP assumes the invited person already has an account; a full
        # invite-by-email-with-signup-link flow is future scope.
        user = User.objects.filter(email__iexact=value).first()
        if user is None:
            raise serializers.ValidationError("Bu e-posta ile kayıtlı kullanıcı bulunamadı.")
        self.user = user
        return value
