from rest_framework import serializers


class CounsellorInputSerializer(serializers.Serializer):
    """Types only. Exact-message rules live in counsellors.services."""

    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    mobile = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    streams = serializers.JSONField(required=False)
    expected_session_min = serializers.IntegerField(required=False, allow_null=True)
    centre_id = serializers.IntegerField(required=False, allow_null=True)
    desk_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        out = super().to_internal_value(data)
        return {k: v for k, v in out.items() if not (k == "expected_session_min" and v is None)}


class PostingInputSerializer(serializers.Serializer):
    centre_id = serializers.IntegerField(required=False)
    desk_label = serializers.CharField(required=False, allow_blank=True)


class DutySerializer(serializers.Serializer):
    duty = serializers.CharField(required=False, allow_blank=True, allow_null=True)
