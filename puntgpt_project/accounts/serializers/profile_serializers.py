from rest_framework import serializers
from accounts.models import User
from django.contrib.auth.password_validation import validate_password

class ProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["name", "email", "phone"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        full_name = f"{instance.first_name} {instance.last_name}".strip()
        data["name"] = full_name
        return data

    def update(self, instance, validated_data):
        name = validated_data.pop("name", None)

        if name:
            name = name.strip()
            parts = name.split()

            if len(parts) == 1:
                # Only first name provided
                instance.first_name = parts[0]
                instance.last_name = ""
            else:
                # Multiple parts → first is first_name, rest join into last_name
                instance.first_name = parts[0]
                instance.last_name = " ".join(parts[1:])

        # Update email/phone normally
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance
    


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "New passwords do not match."})

        # Django built-in password validators
        validate_password(attrs["new_password"])

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
    



    




    

