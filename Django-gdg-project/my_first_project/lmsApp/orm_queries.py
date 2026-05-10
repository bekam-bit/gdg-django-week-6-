from django.db.models import Count, Q
from .models import Member
from django.utils import timezone


def books_with_loan_count(queryset):
    return queryset.annotate(loan_count=Count('loans'))


def never_loaned_books(queryset):
    return queryset.filter(loans=None)


def filtered_books(queryset, category_name, author_name):
    return queryset.filter(
        category__category_name=category_name,
        author__author_name=author_name,
    ).distinct()


def members_with_active_loans(queryset=None):
    
    if queryset is None:
        queryset=Member.objects.all()

    return queryset.annotate(active_loans=Count('loans', filter=Q(loans__return_date__isnull=True)))

def member_has_overdue_loans(member):
    return member.loans.filter(return_date__isnull=True, due_date__lt=timezone.now().date()).exists()


def categories_with_book_count(queryset):
    return queryset.annotate(book_count=Count('books'))