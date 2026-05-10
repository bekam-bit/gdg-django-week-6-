from django.contrib import admin
from django.core.exceptions import PermissionDenied
from typing import Callable
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.utils import timezone
from .models import Author, Book, Category, Loan, Member
from .orm_queries import (
    books_with_loan_count,
    categories_with_book_count,
    filtered_books,
    members_with_active_loans,
    never_loaned_books,
)

def _wrap_admin_only(view_func):
    def _wrapped(request, extra_context=None):
        if not request.user.is_authenticated or getattr(request.user, "role", None) != "admin":
            raise PermissionDenied
        return view_func(request, extra_context)

    return _wrapped


# Allow admin access for staff, but restrict password change to role=admin only.
if not hasattr(admin.site, "_original_password_change"):
    admin.site._original_password_change = admin.site.password_change

if not hasattr(admin.site, "_original_password_change_done"):
    admin.site._original_password_change_done = admin.site.password_change_done

admin.site.password_change = _wrap_admin_only(admin.site._original_password_change)
admin.site.password_change_done = _wrap_admin_only(admin.site._original_password_change_done)

# Restrict auth models in admin: staff can access admin UI but not manage users/groups.
User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass
class AccessPredicateAdminMixin:
    access_predicate: Callable[[object], bool] = lambda self, user: False

    def _has_access(self, request):
        return self.access_predicate(request.user)

    def has_module_permission(self, request):
        return self._has_access(request)

    def has_view_permission(self, request, obj=None):
        return self._has_access(request)

    def has_add_permission(self, request):
        return self._has_access(request)

    def has_change_permission(self, request, obj=None):
        return self._has_access(request)

    def has_delete_permission(self, request, obj=None):
        return self._has_access(request)


@admin.register(User)
class UserAdmin(AccessPredicateAdminMixin, DjangoUserAdmin):
    access_predicate = lambda self, user: user.is_superuser

# Register your models here.
class AvailbilityFilter(admin.SimpleListFilter):
    title="Availability"
    parameter_name="availability"

    def lookups(self, request, model_admin):
        return(
            ("available","Available"),
            ("not_available","Not Available"),
            )
    
    def queryset(self, request, queryset):
        if self.value()=="available":
            return queryset.filter(available_copies__gt=0)
        if self.value()=="not_available":
            return queryset.filter(available_copies__lte=0)
        return queryset


class AuthorFilter(admin.SimpleListFilter):
    title = "Author"
    parameter_name = "author"

    def lookups(self, request, model_admin):
        return [(author.pk, author.author_name) for author in Author.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(author_id=self.value())
        return queryset


class NeverLoanedFilter(admin.SimpleListFilter):
    title = "Loan status"
    parameter_name = "loan_status"

    def lookups(self, request, model_admin):
        return (
            ("never", "Never loaned"),
        )

    def queryset(self, request, queryset):
        if self.value() == "never":
            return never_loaned_books(queryset)
        return queryset


class AuthorCategoryFilter(admin.SimpleListFilter):
    title = "Author + Category"
    parameter_name = "author_category"

    def lookups(self, request, model_admin):
        pairs = Book.objects.values_list(
            "author_id",
            "author__author_name",
            "category__category_id",
            "category__category_name",
        ).distinct()
        return [
            (f"{author_id}:{category_id}", f"{author_name} / {category_name}")
            for author_id, author_name, category_id, category_name in pairs
        ]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        try:
            author_id, category_id = self.value().split(":", 1)
        except ValueError:
            return queryset
        author = Author.objects.filter(pk=author_id).first()
        category = Category.objects.filter(pk=category_id).first()
        if not author or not category:
            return queryset
        return filtered_books(
            queryset,
            category.category_name,
            author.author_name,
        )

class LMSStaffAccessAdmin(AccessPredicateAdminMixin, admin.ModelAdmin):
    access_predicate = lambda self, user: user.is_staff


@admin.register(Book)
class BookAdmin(LMSStaffAccessAdmin):
    list_display=('title','author','available_copies','loan_count')
    list_filter=(AuthorFilter,'category',AuthorCategoryFilter,AvailbilityFilter,NeverLoanedFilter)
    search_fields=('title','ISBN')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return books_with_loan_count(queryset)

    @admin.display(ordering='loan_count', description='Loans')
    def loan_count(self, obj):
        return obj.loan_count


@admin.register(Author)
class AuthorAdmin(LMSStaffAccessAdmin):
    list_display = ("author_name", "author_email")
    search_fields = ("author_name", "author_email")


@admin.register(Category)
class CategoryAdmin(LMSStaffAccessAdmin):
    list_display = ("category_name", "book_count")
    search_fields = ("category_name",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return categories_with_book_count(queryset)

    @admin.display(ordering='book_count', description='Books')
    def book_count(self, obj):
        return obj.book_count


@admin.register(Member)
class MemberAdmin(LMSStaffAccessAdmin):
    list_display = ("member_name", "email", "joined_date", "active_loans")
    search_fields = ("member_name", "email")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return members_with_active_loans(queryset)

    @admin.display(ordering='active_loans', description='Active loans')
    def active_loans(self, obj):
        return obj.active_loans


@admin.register(Loan)
class LoanAdmin(LMSStaffAccessAdmin):
    list_display = ("book", "member", "start_date", "return_date", "status")
    list_filter = ("status", "start_date")
    # Custom action to mark as returned
    actions = ['mark_as_returned']
    
    # We removed readonly_fields for due_date so the JS can update the Input field visually
    # The Signal will still enforce the correct calculation on save if needed, 
    # but this allows the user to see the date populate.
    
    fieldsets = (
        (None, {
            'fields': ('book', 'member', 'status')
        }),
        ('Dates (Auto-Calculated)', {
            'fields': ('start_date', 'due_date', 'return_date'),
            'description': "Start Date and Due Date are automatically set based on the approved Loan Request duration when you select a member and a book."
        }),
    )
    
    class Media:
        js = ('js/admin_loan_date_filler.js',) 


    @admin.action(description='Mark selected loans as Returned')
    def mark_as_returned(self, request, queryset):
        # Iterate over qs to check each loan individually
        updated_count = 0
        failed_count = 0
        
        for loan in queryset:
            if loan.status == "RETURNED":
                continue # Already returned
                
            # Check for overdue logic requested by user
            
            # Check if overdue and check if fines are paid
            if loan.is_overdue:
                # Check for unpaid transaction
                # Assuming 'transactions' is related name
                unpaid = loan.transactions.filter(status="UNPAID").exists()
                if unpaid:
                     # Block return if unpaid fines exist
                    self.message_user(request, f"Skipped '{loan}': Overdue with UNPAID fines. Please collect payment first.", level='ERROR')
                    failed_count += 1
                    continue
            
            # If we reach here, either not overdue OR overdue but paid/no fine
            loan.status = "RETURNED"
            # Setting return_date to now if not set
            if not loan.return_date:
                loan.return_date = timezone.now().date()
            loan.save()
            updated_count += 1
            
        if updated_count > 0:
            self.message_user(request, f"Successfully returned {updated_count} loans.", level='SUCCESS')
        if failed_count > 0:
            self.message_user(request, f"Failed to return {failed_count} loans due to unpaid fines.", level='WARNING')
