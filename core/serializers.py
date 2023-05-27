from django.contrib.auth import authenticate
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=True
    )

    def validate(self, attr):
        user = authenticate(
            email=attr.get('email'),
            password=attr.get('password')
        )

        if not user:
            raise serializers.ValidationError(
                _('Unable to authenticate with provided credentials.'),
                code='authorization'
            )

        attr['user'] = user
        return attr
