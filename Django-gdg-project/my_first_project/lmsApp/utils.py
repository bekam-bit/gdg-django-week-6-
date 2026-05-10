from django.utils import timezone
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from lmsApp.models import LoanRequest

def expire_loans():
    from lmsApp.staffLoanRequestView import send_notification_logic
    now = timezone.now()

    # 1. Mark overdue approvals as EXPIRED
    loans_to_expire = LoanRequest.objects.filter(
        status="APPROVED",
        pickup_until__lt=now
    )

    for loan in loans_to_expire:
        with transaction.atomic():
            loan.status = "EXPIRED"
            loan.save()

            send_notification_logic(loan)

    # 2. Remove EXPIRED requests after 10 days
    # We use pickup_until as the reference point for when it expired
    cutoff_date = now.date() - timezone.timedelta(days=10)
    
    old_expired_requests = LoanRequest.objects.filter(
        status="EXPIRED",
        pickup_until__lt=cutoff_date
    )
    
    if old_expired_requests.exists():
        count = old_expired_requests.count()
        old_expired_requests.delete()
        print(f"Cleaned up {count} old expired loan requests.")

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }