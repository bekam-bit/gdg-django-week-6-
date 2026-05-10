from django.db import models
from django.utils import timezone
from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings

# Create your models here.
class Author(models.Model):
    author_id=models.AutoField(primary_key=True)
    author_name=models.CharField(max_length=150)
    author_email=models.EmailField(max_length=100)
    author_bio=models.TextField(blank=True,null=True)

    def __str__(self):
        return self.author_name

class Category(models.Model):
    category_id=models.AutoField(primary_key=True)
    category_name=models.CharField(max_length=100)

    def __str__(self):
        return self.category_name
    
class Book(models.Model):
    book_id=models.AutoField(primary_key=True)
    ISBN=models.CharField(max_length=50)
    title=models.CharField(max_length=200)
    total_copies=models.IntegerField()
    available_copies=models.IntegerField(null=True, blank=True)
    publication_date=models.DateField()
    max_loan_duration=models.IntegerField(null=True,blank=True)
    location=models.CharField(max_length=20, default="SHELF-01")
    author=models.ForeignKey(Author,on_delete=models.CASCADE,related_name='books')
    category=models.ManyToManyField(Category,related_name='books')

    def __str__(self):
        return self.title
    
    @property
    def is_available(self):
        return self.available_copies>0
    
    def save(self,*args,**kwargs):
        if self.pk:
            # Count any loan that is NOT 'RETURNED' (Includes 'ACTIVE' and 'OVERDUE')
            active_loans=self.loans.exclude(status="RETURNED").count()
            self.available_copies=max(self.total_copies-active_loans,0)
        elif self.available_copies is None:
            self.available_copies=self.total_copies
        super().save(*args,**kwargs)

class Member(models.Model):
    member_id=models.AutoField(primary_key=True)
    member_name=models.CharField(max_length=150)
    email=models.EmailField(max_length=100)
    role=models.CharField(max_length=20, default="Student")
    department=models.CharField(max_length=80, default="CS")
    dorm=models.CharField(max_length=10, default="Block-A")
    joined_date=models.DateField(auto_now_add=True)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='member',null=True,blank=True)

    def __str__(self):
        return f"{self.member_name}"

class Loan(models.Model):
    loan_id=models.AutoField(primary_key=True)
    start_date=models.DateField(default=timezone.now)
    due_date=models.DateField(default=timezone.now)
    return_date=models.DateField(null=True,blank=True)
    book=models.ForeignKey(Book,on_delete=models.PROTECT,related_name='loans')
    member=models.ForeignKey(Member,on_delete=models.PROTECT,related_name='loans')
    STATUS_CHOICES=[
        ("ACTIVE", "Active"),
        ("OVERDUE", "Overdue"),
        ("RETURNED", "Returned"),
    ]
    status=models.CharField(max_length=15,choices=STATUS_CHOICES,default="ACTIVE")

    def __str__(self):
        return f"{self.book.title} loaned to {self.member.member_name}"
    
    @property
    def is_overdue(self):
        if self.status=="RETURNED":
            # If returned, compare return_date with due_date
            if self.return_date and self.return_date > self.due_date:
                return True
            return False
        
        # If not returned, compare current date with due_date
        return timezone.now().date() > self.due_date
    
    def clean(self):
        # Check if this is a new loan (not an update)
        if not self.pk:
            
            LoanRequest = apps.get_model('lmsApp', 'LoanRequest')
            
            # Check for an APPROVED, unfulfilled request
            # We filter by member and book. status must be APPROVED. loan must be None (not yet fulfilled).
            valid_request = LoanRequest.objects.filter(
                member=self.member,
                book=self.book,
                status='APPROVED',
                loan__isnull=True
            ).exists()
            
            if not valid_request:
                raise ValidationError("Using Strict Mode: Cannot create a loan without an existing 'APPROVED' Loan Request. Please ensure the request is approved and not expired.")

    def save(self, *args, **kwargs):
        self.clean() # Enforce validation on save as well for scripted creation
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["book", "status"]),
            models.Index(fields=["due_date", "status"]),
            models.Index(fields=["member", "return_date"]),
        ]

class LoanRequest(models.Model):
    loan_reqeust_id=models.AutoField(primary_key=True)
    requested_duration=models.IntegerField()
    agreed_to_policy=models.BooleanField(default=False)
    created_at=models.DateField(auto_now_add=True)
    approved_at=models.DateField(null=True,blank=True)
    pickup_until=models.DateField(null=True,blank=True)
    pickup_limit=models.IntegerField(default=3)
    STATUS_CHOICES=[
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
        ("LOANED", "Loaned"),
        ("COMPLETED", "Completed"),
    ]
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default="PENDING")
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='loan_requests_member')
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name='loan_requests_book')
    loan=models.OneToOneField(Loan,on_delete=models.CASCADE,related_name="loan_requests_loan", null=True, blank=True)

    def __str__(self):
        return f"{self.member.member_name} sends a loan request for{self.book.book_title} "

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["book", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["member", "book", "status"]),
        ]
    
class Transaction(models.Model):
    transaction_id=models.AutoField(primary_key=True)
    type=models.CharField(max_length=20,null=True,blank=True)
    amount=models.DecimalField(max_digits=10,decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)
    daily_rate=models.DecimalField(max_digits=10,decimal_places=2)
    STATUS_CHOICES = [
    ("PAID", "Paid"),
    ("UNPAID", "Unpaid"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="UNPAID")

    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='transactions')
    loan=models.ForeignKey(Loan,on_delete=models.CASCADE,related_name="transactions")

    def __str__(self):
        return f"{self.member.member_name} -{self.transaction_id} - {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["loan", "status"]),
            models.Index(fields=["member", "created_at"]),
        ]

class Notification(models.Model):
    notification_id=models.AutoField(primary_key=True)
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='notifications')
    loan_request=models.ForeignKey(LoanRequest,on_delete=models.CASCADE,related_name='notifications')
    message=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    is_read=models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.member.member_name}"

    class Meta:
        indexes = [
            models.Index(fields=["member", "is_read"]),
            models.Index(fields=["member", "created_at"]),
            models.Index(fields=["loan_request", "created_at"]),
        ]

class User(AbstractUser):
    ROLE_CHOICES= (
        ('admin','Admin'),
        ('staff','Staff'),
        ('member', 'Member'),
    )

    role = models.CharField(max_length=20,choices=ROLE_CHOICES,default="member")
