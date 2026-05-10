from datetime import timedelta
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.utils import timezone
from .models import Loan, Book, LoanRequest, Transaction, Notification
from django.core.exceptions import ValidationError

@receiver(pre_delete, sender=Loan)
def check_loan_return_status(sender, instance, **kwargs):
    # Check for unpaid fines
    unpaid_fines = instance.transactions.filter(status="UNPAID").exists()
    if unpaid_fines:
        raise ValidationError(f"Cannot delete loan for '{instance.book.title}' because there are UNPAID fines. Please settle the payment first.")
    
    # If overdue but no fine transaction generated yet?
    # Logic: if overdue and not returned, we might want to block too.
    if instance.is_overdue and not instance.status == "RETURNED":
         # If no transaction exists (meaning fine not paid), we block deletion.
         transactions = instance.transactions.filter(status="PAID").exists()
         if not transactions:
            # If overdue and fine not paid (or not even created), block.
            raise ValidationError(f"Cannot delete OVERDUE loan for '{instance.book.title}' without settling fines. Please generate and pay the fine first.")

@receiver(pre_save, sender=Loan)
def store_prev_state(sender, instance, **kwargs):
    if instance.pk:
        prev = sender.objects.get(pk=instance.pk)
        instance._prev_status = prev.status
    else:
        instance._prev_status = None

@receiver(post_save, sender=Loan)
def manage_loan_creation(sender, instance, created, **kwargs):
    book = instance.book
    
    if created:
        # 1. Update book copies
        if book.available_copies > 0:
            book.available_copies -= 1
            book.save()
        else:
            pass

        # 2. Link to existing approved request and SET DATES based on CREATION TIME
        # This guarantees that the loan starts NOW (at creation), not at approval time.
        # Use filter().update() to avoid infinite recursion of post_save
        today = timezone.now().date()
        
        # Check if there is an approved request for this user/book that needs linking
        # This handles the case where staff creates loan manually in Admin
        approved_request = LoanRequest.objects.filter(
            member=instance.member, 
            book=instance.book, 
            status='APPROVED', 
            loan__isnull=True
        ).first()

        if approved_request:
            # Link the loan and update status to LOANED to remove from active staff list
            approved_request.loan = instance
            approved_request.status = "LOANED"
            approved_request.save()
            
            # Update the loan's start_date to TODAY and calculate due_date based on request duration
            # Only if the admin didn't manually set a far future date (simple check: if start_date is today)
            
            # Start date is TODAY (creation date)
            new_due_date = today + timedelta(days=approved_request.requested_duration)
            
            # We use update() on the QuerySet to modify the record in DB without triggering signals again
            Loan.objects.filter(pk=instance.pk).update(start_date=today, due_date=new_due_date)

            # Send Notification to Member
            try:
                message = (
                    f"Your loan for '{instance.book.title}' has been recorded and started today ({today}). "
                    f"Duration: {approved_request.requested_duration} days. "
                    f"Please return it by {new_due_date}. "
                    f"Note: A daily fine will apply for every day the return is overdue."
                )
                Notification.objects.create(
                    member=instance.member,
                    loan_request=approved_request,
                    message=message,
                    is_read=False
                )
            except Exception as e:
                # Log error or pass silently if notification system fails, to avoid breaking loan creation
                print(f"Failed to send loan start notification: {e}")
            
        else:
            # Even if no request exists (pure manual loan), ensure start_date is today if deemed necessary
            # or just respect what admin entered. 
            pass

    # Handle return logic
    elif instance._prev_status != "RETURNED" and instance.status == "RETURNED":
        book.available_copies += 1
        book.save()
        
        # Link to Update Request Status to COMPLETED to remove from Loaned List
        # Try to find the linked request
        try:
            linked_request = instance.loan_requests_loan  # related_name from LoanRequest model
            linked_request.status = "COMPLETED"
            linked_request.save()

            # Send Notification: Return Successful
            message = (
                f"Your loan for '{instance.book.title}' has been successfully returned. "
                f"Thank you! You are now eligible to apply for this book again if needed."
            )
            Notification.objects.create(
                member=instance.member,
                loan_request=linked_request,
                message=message,
                is_read=False
            )
        except Exception as e:
             # Might be a manual loan with no request or notification failed
             pass


@receiver(post_delete, sender=Loan)
def restore_available_copies_on_delete(sender, instance, **kwargs):
    book = instance.book
    if instance.status != "RETURNED":
        book.available_copies += 1
        book.save()