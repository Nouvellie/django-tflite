import uuid

from .models import User
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.signals import user_logged_in
from main.exceptions import CustomError
from rest_framework.authtoken.models import Token
from rest_framework import serializers


# HELP TEXT.
PASSWORD_HELP_TEXT = f"Please enter a file or text (code) to be processed with the Stackoverflow model. The filename cannot be longer than 50 characters and the allowed formats are '.md, .txt, .docx'. (In case both parameters are sent, the file is validated first and only one is answered.)"


class UserSerializer(serializers.ModelSerializer):
    """Returns a modified serialized dictionary of the user model."""

    class Meta:
        model = User
        fields = ('username', 'email', 'is_verified',)


class UserInfoSerializer(serializers.ModelSerializer):
    """Returns a modified serialized info dictionary of the user model."""

    class Meta:
        model = User
        fields = ('username', 'email', 'is_verified',
                  'date_joined', 'first_name', 'last_name',)


class SignUpSerializer(serializers.ModelSerializer):
    """This class serializes the creation of a new account, with all the validations are ok."""

    password = serializers.CharField(
        write_only=True,
        label="Password",
        validators=[validate_password],
        trim_whitespace=False,
        style={'input_type': 'password', }
    )
    password2 = serializers.CharField(
        write_only=True,
        label="Confirm Password",
        validators=[validate_password],
        trim_whitespace=False,
        style={'input_type': 'password', }
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2',)

    def create(self, validated_data: dict) -> User:
        """User creation."""
        password = validated_data.pop('password', None)
        validated_data.pop('password2', None)
        new_user = self.Meta.model(**validated_data)
        if password is not None:
            new_user.set_password(password)
        new_user.save()
        user = User.objects.get(username=new_user.username)
        Token.objects.create(user=user)
        return user

    def validate(self, attrs: dict) -> dict:
        """SignUp data validation."""
        if attrs['password'] != attrs['password2']:
            raise CustomError(
                detail={'error': "Password fields didn't match."}, code=400)
        if attrs['username'] == attrs['password']:
            raise CustomError(
                detail={'error': "For your security the username and password cannot be the same."}, code=403)
        if attrs['password'] == attrs['email'].split("@")[0]:
            raise CustomError(
                detail={'error': "For your security the email and password cannot be the same."}, code=403)
        if attrs['password'].startswith(str(attrs['email'].split("@")[0][:4])):
            raise CustomError(
                detail={'error': "For your security, the password cannot contain your e-mail address."}, code=403)
        if attrs['password'].startswith(str(attrs['username'][:4])):
            raise CustomError(
                detail={'error': "For your security, the password cannot contain your username."}, code=403)
        if attrs['username'] == attrs['email'].split("@")[0]:
            raise CustomError(
                detail={'error': "For your security the username and email address cannot be the same."}, code=403)
        # Validation @email.
        # if attrs['email'].split("@")[1].split(".")[0].lower() != 'nouvellie':
        #     raise CustomError(
        #         detail="The e-mail does not correspond to those allowed in the system.", code=403)
        return super().validate(attrs)


class SignInSerializer(serializers.ModelSerializer):
    """Validates the credentials of an account when signin."""

    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        label="Password",
        trim_whitespace=False,
        style={'input_type': 'password', }
    )

    class Meta:
        model = User
        fields = ('username', 'password',)

    def validate(self, attrs: dict) -> dict:
        """SignIn data validation."""
        user = authenticate(**attrs)
        if user:
            user.acc_hash = uuid.uuid4()
            user.acc_hash_expiration = datetime.now(timezone.utc)
            user.save()
            if user.is_active:
                attrs.update({'user': user})
                return super().validate(attrs)
            elif not user.is_active:
                raise CustomError(
                    detail={'error': "This account has been deactivated by an administrator."}, code=403)
        else:
            raise CustomError(
                detail={'error': "Incorrect credentials."}, code=401)

    def get_user(self) -> User:
        """Return User."""
        return list(self.validated_data.items())[-1][1]


class TokenInfoSerializer(serializers.Serializer):

    token = serializers.CharField(
        label="Token", help_text="Token hash. (unique)")

    class Meta:
        fields = ('token',)


class AccountVerificationSerializer(serializers.ModelSerializer):

    acc_hash = serializers.CharField(
        write_only=True,
        label="Hash",
        help_text="Hash link sent to email."
    )

    class Meta:
        model = User
        fields = ('acc_hash',)

    def validate(self, attrs: dict) -> dict:
        """Hash validation."""
        acc_hash = attrs['acc_hash']
        if not User.objects.filter(acc_hash=acc_hash).exists():
            raise CustomError(
                detail={'error': "The verification link is invalid, please request a new one."}, code=403)

        user = User.objects.get(acc_hash=acc_hash)
        timenow = datetime.now(timezone.utc)
        if timenow > (user.acc_hash_expiration + timedelta(days=1)):
            raise CustomError(detail={'error': "Link has expired."}, code=400)

        elif not user.is_active:
            raise CustomError(
                detail={'error': "This account cannot be verified because it has been deactivated by an administrator."}, code=403)
        elif user.is_verified:
            raise CustomError(
                detail={'error': "This account has already been verified."}, code=202)
        else:
            user.is_verified = True
            user.acc_hash = uuid.uuid4()
            user.acc_hash_expiration = datetime.now(timezone.utc)
            user.save()
            return super().validate(attrs)


class PasswordResetSerializer(serializers.ModelSerializer):

    pass_token = serializers.CharField(
        write_only=True,
        label="PassToken",
    )
    password = serializers.CharField(
        write_only=True,
        label="NewPassword",
        trim_whitespace=False,
        validators=[validate_password],
        style={'input_type': 'password', }
    )

    class Meta:
        model = User
        fields = ('pass_token', 'password')

    def validate(self, attrs: dict) -> dict:
        """Password validation."""
        if not User.objects.filter(pass_token=attrs['pass_token']).exists():
            raise CustomError(
                detail={'error': "The token is invalid, please request a new one."}, code=403)
        user = User.objects.get(pass_token=attrs['pass_token'])
        timenow = datetime.now(timezone.utc)
        if timenow > (user.pass_token_expiration + timedelta(days=1/12)):
            raise CustomError(detail={'error': "Link has expired."}, code=400)
        elif attrs['password'] == user.email.split("@")[0]:
            raise CustomError(
                detail={'error': "For your security the email and password cannot be the same."}, code=403)
        elif attrs['password'].startswith(str(user.email.split("@")[0][:4])):
            raise CustomError(
                detail={'error': "For your security, the password cannot contain your email address."}, code=403)
        elif attrs['password'].startswith(str(user.username[:4])):
            raise CustomError(
                detail={'error': "For your security, the password cannot contain your username."}, code=403)
        user.set_password(attrs['password'])
        user.pass_token = uuid.uuid4()
        user.pass_token_expiration = datetime.now(timezone.utc)
        user.save()
        return super().validate(attrs)
