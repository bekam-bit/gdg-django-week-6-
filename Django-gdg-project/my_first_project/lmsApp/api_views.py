from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Author, Book, Category, Loan, LoanRequest, Member, Notification, Transaction
from .serrializer import (
    AuthorSerializer,
    BookSerializer,
    CategorySerializer,
    LoanRequestSerializer,
    LoanSerializer,
    MemberSerializer,
    NotificationSerializer,
    TransactionSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all().select_related("author").prefetch_related("category")
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all().select_related("user")
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated]


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all().select_related("book", "member")
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]


class LoanRequestViewSet(viewsets.ModelViewSet):
    queryset = LoanRequest.objects.all().select_related("member", "book", "loan")
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated]


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().select_related("member", "loan")
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().select_related("member", "loan_request")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([AllowAny])
def register_api(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        payload = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": getattr(user, "role", None),
        }
        return Response(payload, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        return Response(
            {
                "tokens": serializer.validated_data["tokens"],
                "role": serializer.validated_data["role"],
                "username": serializer.validated_data["user"].username,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_api(request):
    return Response({"status": "ok", "service": "lms-api"}, status=status.HTTP_200_OK)
