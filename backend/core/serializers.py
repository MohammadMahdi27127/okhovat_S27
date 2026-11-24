import math
from collections.abc import Mapping
from datetime import timedelta
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import User


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({"non_field_errors": ["فیلد ناشناخته در درخواست."]})
        return super().to_internal_value(data)


class LoginInput(StrictSerializer):
    code = serializers.RegexField(r"^[0-9]{1,40}$", max_length=40)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class UserOutput(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["code", "name", "ring", "team", "is_coach", "is_admin",
                  "is_ring_leader", "is_workgroup_manager", "is_concerned_member"]


class RegisterInput(LoginInput):
    name = serializers.CharField(max_length=120)
    ring = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    team = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    is_coach = serializers.BooleanField(default=False)
    is_admin = serializers.BooleanField(default=False)
    is_ring_leader = serializers.BooleanField(default=False)
    is_workgroup_manager = serializers.BooleanField(default=False)
    is_concerned_member = serializers.BooleanField(default=False)

    def validate(self, data):
        candidate = User(**{key: value for key, value in data.items() if key != "password"})
        try:
            validate_password(data["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages})
        return data


class FiniteFloat(serializers.FloatField):
    def to_internal_value(self, value):
        result = super().to_internal_value(value)
        if not math.isfinite(result):
            raise serializers.ValidationError("عدد باید محدود و معتبر باشد.")
        return result


class GrowthInput(StrictSerializer):
    day = serializers.DateField()
    dateJalali = serializers.CharField(max_length=32)
    sport = FiniteFloat(min_value=0, max_value=24)
    reading = serializers.IntegerField(min_value=0, max_value=10000)
    publish = serializers.BooleanField(default=False)
    skillTitle = serializers.CharField(max_length=250, allow_blank=True, default="")
    learned = serializers.CharField(max_length=10000, allow_blank=True, default="")
    practice = serializers.CharField(max_length=10000, allow_blank=True, default="")
    responsibility = serializers.CharField(max_length=2000, allow_blank=True, default="")
    leisure = serializers.ChoiceField(choices=["", "خواب", "ورزش", "بازی", "شبکه‌های اجتماعی"], default="")
    proof = serializers.CharField(max_length=100, allow_blank=True, default="")
    proofName = serializers.CharField(max_length=255, allow_blank=True, default="")

    def validate_day(self, value):
        if value > timezone.localdate() or value < timezone.localdate() - timedelta(days=366):
            raise serializers.ValidationError("تاریخ باید در یک سال گذشته باشد.")
        return value


class PostInput(StrictSerializer):
    title = serializers.CharField(max_length=300)
    text = serializers.CharField(max_length=20000)
    type = serializers.ChoiceField(choices=["شخصی", "حلقه", "کارگروه"], default="شخصی")
    attachment = serializers.CharField(max_length=100, allow_blank=True, default="")
    fileName = serializers.CharField(max_length=255, allow_blank=True, default="")
    location = serializers.CharField(max_length=200, allow_blank=True, default="")
    when = serializers.DateTimeField(required=False, allow_null=True)
    people = serializers.ListField(child=serializers.CharField(max_length=40), max_length=500, default=list)


class ToggleInput(StrictSerializer):
    active = serializers.BooleanField()


class CommentInput(StrictSerializer):
    text = serializers.CharField(max_length=2000)
    parent = serializers.CharField(max_length=65, required=False, allow_null=True)


class MessageInput(StrictSerializer):
    scope = serializers.ChoiceField(choices=["all", "group", "ring", "person"])
    target = serializers.CharField(max_length=120, allow_blank=True, default="")
    text = serializers.CharField(max_length=4000)


class GradeInput(StrictSerializer):
    target = serializers.CharField(max_length=120)
    score = FiniteFloat(min_value=0, max_value=10000)


class StatusInput(StrictSerializer):
    sportPlan = serializers.CharField(max_length=2000, allow_blank=True)
    currentBook = serializers.CharField(max_length=300, allow_blank=True)


class PasswordInput(StrictSerializer):
    current = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class QuestionInput(StrictSerializer):
    message = serializers.CharField(max_length=2000)


class FormInput(StrictSerializer):
    title = serializers.CharField(max_length=200)
    questions = serializers.ListField(child=serializers.CharField(max_length=300), min_length=1, max_length=20)


class LandingInput(StrictSerializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=4000)


class RoleInput(StrictSerializer):
    is_coach = serializers.BooleanField()
    is_admin = serializers.BooleanField()
    is_ring_leader = serializers.BooleanField()
    is_workgroup_manager = serializers.BooleanField()
    is_concerned_member = serializers.BooleanField(default=False)
    ring = serializers.CharField(max_length=120, allow_blank=True)
    team = serializers.CharField(max_length=120, allow_blank=True)
    bale_id = serializers.CharField(max_length=100, allow_blank=True, default="")


class AvatarInput(StrictSerializer):
    url = serializers.CharField(max_length=100, allow_blank=True)


class SuspendInput(StrictSerializer):
    days = serializers.ChoiceField(choices=[1, 3])


class AnswersInput(StrictSerializer):
    answers = serializers.ListField(child=serializers.CharField(max_length=4000, allow_blank=True), max_length=20)
