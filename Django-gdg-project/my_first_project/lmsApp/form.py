from django import forms
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from . models import Book,LoanRequest,Transaction,User,Member
from .orm_queries import member_has_overdue_loans

class BookForm(forms.ModelForm):
   class Meta:
        model = Book
        fields = ['ISBN', 'title', 'total_copies', 'publication_date', 'author','category', 'max_loan_duration','location']
        widgets = {
            'publication_date': forms.DateInput(attrs={'type': 'date'}),
        }
class LoanRequestForm(forms.ModelForm):

    class Meta:
        model=LoanRequest
        fields=['requested_duration','agreed_to_policy']
        widgets={
            'agreed_to_policy':forms.CheckboxInput(attrs={'type':'checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super(LoanRequestForm, self).__init__(*args, **kwargs)
        self.fields['agreed_to_policy'].required = True


    def clean_requested_date(self):
        requested_date=self.cleaned_data.get('requested_date')
        
        if requested_date and requested_date < timezone.now().date():
            raise forms.ValidationError("Requested date cannot be in the past.")

        return requested_date

    def clean(self):
        cleaned_data=super().clean()
        
        # Validation logic moved to view where book/member context is available
        return cleaned_data

    def clean_agreed_to_policy(self):
        agreed_to_policy = self.cleaned_data.get('agreed_to_policy')
        if not agreed_to_policy:
            raise forms.ValidationError("You must agree to the library policy.")
        return agreed_to_policy

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'amount', 'daily_rate']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class RegisterForm(forms.ModelForm):
    username=forms.CharField(max_length=150)
    password=forms.CharField(widget=forms.PasswordInput)
    password_confirm=forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model=Member
        fields=['member_name','email','department','dorm']
    
    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data

    def save(self,commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            role='member'
        )

        member = super().save(commit=False)
        member.user=user

        if commit:
                member.save()

        return member