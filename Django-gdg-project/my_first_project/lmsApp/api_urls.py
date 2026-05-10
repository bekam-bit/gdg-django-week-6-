from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .api_views import (
    AuthorViewSet,
    BookViewSet,
    CategoryViewSet,
    LoanRequestViewSet,
    LoanViewSet,
    MemberViewSet,
    NotificationViewSet,
    TransactionViewSet,
    health_api,
    login_api,
    register_api,
)

router = DefaultRouter()
router.register(r"authors", AuthorViewSet, basename="api-authors")
router.register(r"categories", CategoryViewSet, basename="api-categories")
router.register(r"books", BookViewSet, basename="api-books")
router.register(r"members", MemberViewSet, basename="api-members")
router.register(r"loans", LoanViewSet, basename="api-loans")
router.register(r"loan-requests", LoanRequestViewSet, basename="api-loan-requests")
router.register(r"transactions", TransactionViewSet, basename="api-transactions")
router.register(r"notifications", NotificationViewSet, basename="api-notifications")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", health_api, name="api-health"),
    path("auth/register/", register_api, name="api-register"),
    path("auth/login/", login_api, name="api-login"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
