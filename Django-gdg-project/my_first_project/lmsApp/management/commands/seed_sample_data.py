from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from lmsApp.models import Author, Book, Category, Loan, LoanRequest, Member, Notification, Transaction
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Seed sample LMS data for demo/testing."

    def handle(self, *args, **options):
        User = get_user_model()

        admin_user, _ = User.objects.get_or_create(
            username="admin1234",
            defaults={"role": "admin", "is_staff": True, "is_superuser": True},
        )
        if not admin_user.has_usable_password():
            admin_user.set_password("AdminPass123!")
            admin_user.save(update_fields=["password"])

        staff_user, _ = User.objects.get_or_create(
            username="staff1234",
            defaults={"role": "staff", "is_staff": True},
        )
        if not staff_user.has_usable_password():
            staff_user.set_password("StaffPass123!")
            staff_user.save(update_fields=["password"])

        member_user, _ = User.objects.get_or_create(
            username="member1234",
            defaults={"role": "member"},
        )
        if not member_user.has_usable_password():
            member_user.set_password("MemberPass123!")
            member_user.save(update_fields=["password"])

        member, _ = Member.objects.get_or_create(
            user=member_user,
            defaults={
                "member_name": "Samuel Member",
                "email": "member1234@example.com",
                "department": "CS",
                "dorm": "Block-A",
            },
        )

        author1, _ = Author.objects.get_or_create(
            author_name="Chimamanda Adichie",
            defaults={"author_email": "adichie@example.com"},
        )
        author2, _ = Author.objects.get_or_create(
            author_name="Ngugi wa Thiong'o",
            defaults={"author_email": "ngugi@example.com"},
        )

        category1, _ = Category.objects.get_or_create(category_name="Fiction")
        category2, _ = Category.objects.get_or_create(category_name="History")

        book1, _ = Book.objects.get_or_create(
            ISBN="ISBN-0001",
            defaults={
                "title": "Half of a Yellow Sun",
                "total_copies": 5,
                "publication_date": timezone.now().date(),
                "max_loan_duration": 14,
                "author": author1,
            },
        )
        book1.category.add(category1)

        book2, _ = Book.objects.get_or_create(
            ISBN="ISBN-0002",
            defaults={
                "title": "Decolonising the Mind",
                "total_copies": 3,
                "publication_date": timezone.now().date(),
                "max_loan_duration": 10,
                "author": author2,
            },
        )
        book2.category.add(category2)

        loan_request, _ = LoanRequest.objects.get_or_create(
            member=member,
            book=book1,
            defaults={
                "requested_duration": 7,
                "agreed_to_policy": True,
                "approved_at": timezone.now().date(),
                "pickup_until": timezone.now().date() + timedelta(days=3),
                "status": "APPROVED",
            },
        )

        if loan_request.loan is None:
            loan = Loan.objects.create(
                book=book1,
                member=member,
                start_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=7),
                status="ACTIVE",
            )
            loan_request.loan = loan
            loan_request.status = "LOANED"
            loan_request.save(update_fields=["loan", "status"])

            Transaction.objects.get_or_create(
                member=member,
                loan=loan,
                defaults={
                    "type": "FINE",
                    "amount": 0.00,
                    "daily_rate": 1.50,
                    "status": "PAID",
                },
            )

            Notification.objects.get_or_create(
                member=member,
                loan_request=loan_request,
                defaults={
                    "message": "Your loan request has been approved. Please pick up the book.",
                },
            )

        self.stdout.write(self.style.SUCCESS("Sample data seeded."))
