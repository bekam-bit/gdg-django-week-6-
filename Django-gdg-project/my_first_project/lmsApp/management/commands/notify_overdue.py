from django.core.management.base import BaseCommand
from django.utils import timezone
from lmsApp.models import Loan, Notification

class Command(BaseCommand):
    help = "Check for overdue loans and notify members"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # Only active loans that have passed the due date.
        overdue_loans = Loan.objects.filter(
            status="ACTIVE",
            due_date__lt=today
        ).select_related('member', 'book')
        
        count = 0
        for loan in overdue_loans:
            # Calculate overdue days
            overdue_days = (today - loan.due_date).days
            
            # Construct message
            message = (
                f"ALERT: Your loan for '{loan.book.title}' is OVERDUE by {overdue_days} days. "
                f"Please return it immediately to avoid increasing fines."
            )
            
            # Notifications require a LoanRequest; skip if missing to avoid invalid rows.
            try:
                loan_request = loan.loan_requests_loan
            except Loan.loan_requests_loan.RelatedObjectDoesNotExist:
                self.stdout.write(self.style.WARNING(f"Loan {loan.loan_id} has no associated request. Skipping notification."))
                continue

            # Avoid duplicate alerts if the job runs multiple times per day.
            already_notified = Notification.objects.filter(
                member=loan.member,
                loan_request=loan_request,
                message=message,
                created_at__date=today
            ).exists()
            
            if not already_notified:
                Notification.objects.create(
                    member=loan.member,
                    loan_request=loan_request,
                    message=message
                )
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Sent {count} overdue notifications."))
