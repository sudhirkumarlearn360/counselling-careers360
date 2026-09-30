from rest_framework import serializers


class CentreInputSerializer(serializers.Serializer):
    """Parses types only; the business rules and their exact messages live in centres.services."""

    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    venue = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date = serializers.DateField(required=False)
    opens_at = serializers.TimeField(required=False)
    closes_at = serializers.TimeField(required=False)
    expected_students = serializers.IntegerField(required=False, min_value=0)
    front_desk_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    # The centre's front-desk login (required on create, optional on edit; the password is write-only).
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)


class ConfirmSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(required=False, default=False)
