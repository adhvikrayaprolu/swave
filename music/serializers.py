from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile, ProviderToken
from .models import Track, SwipeEvent, Playlist, PlaylistItem


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'display_name')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Try to get user by email
            try:
                user = User.objects.get(email=email)
                # Authenticate with username and password
                user = authenticate(username=user.username, password=password)
                if not user:
                    raise serializers.ValidationError('Invalid credentials')
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled')
                attrs['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid credentials')
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('favorite_genres', 'favorite_artists', 'auto_play_previews', 
                 'swipe_sensitivity', 'total_swipes', 'total_likes', 'total_rejects')


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'display_name', 'date_joined', 'profile')
        read_only_fields = ('id', 'date_joined')


class ProviderTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderToken
        fields = ('provider', 'provider_user_id', 'expires_at', 'created_at')
        read_only_fields = ('expires_at', 'created_at')


class UserWithProvidersSerializer(UserSerializer):
    provider_tokens = ProviderTokenSerializer(many=True, read_only=True)
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('provider_tokens',)


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = "__all__"

class SwipeSerializer(serializers.ModelSerializer):
    track = TrackSerializer()
    class Meta:
        model = SwipeEvent
        fields = ("id", "track", "action", "played_ms", "created_at")

class PlaylistItemSerializer(serializers.ModelSerializer):
    track = TrackSerializer()
    class Meta:
        model = PlaylistItem
        fields = ("track", "position")

class PlaylistSerializer(serializers.ModelSerializer):
    items = PlaylistItemSerializer(many=True, read_only=True)
    class Meta:
        model = Playlist
        fields = ("id", "name", "date", "items", "created_at")
