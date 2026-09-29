from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer, UserWithProvidersSerializer
from .firebase_config import verify_firebase_token, FIREBASE_ADMIN_READY
FIREBASE_ENABLED = FIREBASE_ADMIN_READY


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user (legacy endpoint - Firebase auth is primary)."""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login user (legacy endpoint - Firebase auth is primary)."""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """Refresh JWT access token."""
    refresh_token_val = request.data.get('refresh')
    if not refresh_token_val:
        return Response(
            {'error': 'Refresh token required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        refresh = RefreshToken(refresh_token_val)
        return Response({'access': str(refresh.access_token)})
    except Exception:
        return Response(
            {'error': 'Invalid refresh token'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get current user profile.

    - If the user is authenticated (JWT), return their real profile.
    - Otherwise, return the demo_spotify user profile so the app
      can still use /feed etc. without redirecting to login.
    """
    if request.user and request.user.is_authenticated:
        user = request.user
    else:
        user = request.user

    serializer = UserWithProvidersSerializer(user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile."""
    user = request.user

    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """Logout user."""
    try:
        refresh_token_val = request.data.get('refresh')
        if refresh_token_val:
            token = RefreshToken(refresh_token_val)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception:
        return Response(
            {'error': 'Invalid token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_firebase_token_view(request):
    """Verify Firebase ID token and return Django JWT tokens."""
    firebase_token = request.data.get('firebase_token')
    if not firebase_token:
        return Response(
            {'error': 'Firebase token required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not FIREBASE_ENABLED or not verify_firebase_token:
        return Response(
            {'error': 'Firebase verification not configured'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    decoded_token = verify_firebase_token(firebase_token)
    if not decoded_token:
        return Response(
            {'error': 'Invalid Firebase token'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    email = decoded_token.get('email')
    if not email:
        return Response(
            {'error': 'No email in Firebase token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        username = email.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=email,
            display_name=username
        )
        UserProfile.objects.get_or_create(user=user)
    
    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    })

