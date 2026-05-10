from django.shortcuts import render,redirect, get_object_or_404
from django.db import transaction as db_transaction
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import TemplateHTMLRenderer,JSONRenderer
from .form import LoanRequestForm, PaymentForm
from .models import LoanRequest,Book,Loan,Member,Notification, Transaction
from .serrializer import LoanRequestSerializer, TransactionSerializer
from django.utils import timezone
from datetime import datetime
from .orm_queries import member_has_overdue_loans
from django.urls import reverse
from urllib.parse import urlencode

@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def LoanRequestView(request,book_id,member_id=None,transaction_id=None):
    
    book=get_object_or_404(Book,pk=book_id)

    member = None
    if member_id is not None:
        member = get_object_or_404(Member,pk=member_id)
    elif request.user.is_authenticated and hasattr(request.user, 'member'):
        member = request.user.member

    content_type = (request.content_type or '').lower()
    accept_header = (request.META.get('HTTP_ACCEPT') or '').lower()
    is_browser_form_post = request.method == "POST" and (
        content_type.startswith('application/x-www-form-urlencoded')
        or content_type.startswith('multipart/form-data')
    )
    wants_html = (
        request.accepted_renderer.format == 'html'
        or 'text/html' in accept_header
        or is_browser_form_post
    )

    if request.method == "GET" and member is None:
        accepted_renderer = getattr(request, 'accepted_renderer', None)
        if accepted_renderer and accepted_renderer.format == 'json':
            return Response({"error": "User is not a registered member."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.is_authenticated:
            login_url = reverse('login_member')
            query_string = urlencode({'next': request.get_full_path()})
            return redirect(f"{login_url}?{query_string}")

        return Response(
            {
                'loan_request_form': LoanRequestForm(),
                'book': book,
                'member': None,
                'error': "Authenticated user is not linked to a member profile."
            },
            template_name="lmsApp/loan pages/loan_request_form.html",
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method=="POST":
        if member is None:
            accepted_renderer = getattr(request, 'accepted_renderer', None)
            if accepted_renderer and accepted_renderer.format == 'json':
                return Response({"error": "User is not a registered member."}, status=status.HTTP_400_BAD_REQUEST)

            if not request.user.is_authenticated:
                login_url = reverse('login_member')
                query_string = urlencode({'next': request.get_full_path()})
                return redirect(f"{login_url}?{query_string}")

            return Response(
                {
                    'loan_request_form': LoanRequestForm(),
                    'book': book,
                    'member': None,
                    'error': "Authenticated user is not linked to a member profile."
                },
                template_name="lmsApp/loan pages/loan_request_form.html",
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for overdue loans generally
        has_overdue = member_has_overdue_loans(member)

        # Check a specific transaction if provided, but also block on any unpaid fines.
        transaction = None
        if transaction_id:
            transaction = get_object_or_404(Transaction, pk=transaction_id)

        # Check if member has ANY unpaid transactions
        has_unpaid_fines = Transaction.objects.filter(member=member, status="UNPAID").exists()

        # Always try to render HTML if it's a browser request to this view, or if explicitly requested
        if wants_html:
            loan_request_form=LoanRequestForm(request.POST)

            if loan_request_form.is_valid():
                
                # Create a temporary instance to check values but don't save yet
                temp_loan_request = loan_request_form.save(commit=False)
                
                copies=book.available_copies # Fixed spelling error avialble_copies -> available_copies
                if copies <= 0:
                    loan_request_form.add_error(None,"Not enough available copies.")
                    return Response(
                        {'loan_request_form':loan_request_form,'book':book,'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if book.max_loan_duration and temp_loan_request.requested_duration > book.max_loan_duration:
                    loan_request_form.add_error('requested_duration',"Your length of loan request is more than the maximum loan duration limit.")
                    return Response(
                        {'loan_request_form':loan_request_form,'book':book,'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check for existing active loans for this specific book
                active_loan_exists = Loan.objects.filter(
                    member=member, 
                    book=book
                ).exclude(status='RETURNED').exists()

                if active_loan_exists:
                    loan_request_form.add_error(None, "You already have an active loan for this book. Please return it first.")
                    return Response(
                        {'loan_request_form':loan_request_form, 'book':book, 'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for existing pending or approved requests for this specific book
                existing_request_exists = LoanRequest.objects.filter(
                    member=member,
                    book=book,
                    status__in=['PENDING', 'APPROVED']
                ).exists()

                if existing_request_exists:
                    loan_request_form.add_error(None, "You already have a pending or approved request for this book. Please wait for it to be processed or expire.")
                    return Response(
                        {'loan_request_form':loan_request_form, 'book':book, 'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if has_overdue and has_unpaid_fines:
                    loan_request_form.add_error(None,"Member has overdue loans and unpaid fines. Please settle them first.")
                    return Response(
                        {'loan_request_form':loan_request_form,'book':book,'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )

                with db_transaction.atomic():
                    loan_request=loan_request_form.save(commit=False)
                    loan_request.book=book
                    loan_request.member=member
                    loan_request.save()

                return redirect('loan_request_success')

            else:
                return Response(
                        {'loan_request_form':loan_request_form,'book':book,'member':member},
                        template_name="lmsApp/loan pages/loan_request_form.html",
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            serializer=LoanRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with db_transaction.atomic():
                loan_req=serializer.save(book=book,member=member)
                
            return Response(
                {"data": LoanRequestSerializer(loan_req).data},
                status=status.HTTP_201_CREATED
            )
    else:
        # Check if the accepted renderer is TemplateHTMLRenderer
        if wants_html:
            loan_request_form=LoanRequestForm()
            return Response(
                {'loan_request_form':loan_request_form,'book':book,'member':member},
                template_name="lmsApp/loan pages/loan_request_form.html"
            )
        
        # If not HTML, assume JSON or similar that doesn't need a template_name
        else:
            return Response({
                "book":{"id":book.book_id, "title":book.title, "available_copies":book.available_copies, "max_loan_duration":book.max_loan_duration},
                "member": {"id":member.member_id, "name":member.member_name} if member else None
            })
        
def loan_request_success(request):
    return render(request,'lmsApp/loan pages/loan_request_success.html')

def fine_success(request, transaction_id=None):
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, pk=transaction_id)
    return render(request, 'lmsApp/transaction pages/fine-success.html', {'transaction': transaction})

def no_overdue(request):
    return render(request, 'lmsApp/transaction pages/no_overdue.html')

def recieveNotification(request, notification_id=None):
    # Resolve the member from the current user
    if request.user.is_authenticated and hasattr(request.user, 'member'):
        member = request.user.member
    else:
        # If user is not authenticated or not a member, show empty list or handle as error
        return render(request, "lmsApp/loan pages/notification_list.html", {'notifications': []})

    if notification_id:

        notification=get_object_or_404(
            Notification,
            pk=notification_id,
            member=member
        )

        if not notification.is_read:
            notification.is_read=True
            notification.save(update_fields=['is_read'])

        return render(request,
                      "lmsApp/loan pages/recieve_notification.html",
                      {'notification':notification})

    else:
        notifications=Notification.objects.filter(
            member=member
        ).select_related('loan_request','loan_request__book').order_by('-created_at')

        return render(request,
                      "lmsApp/loan pages/notification_list.html",
                      {'notifications':notifications})


def toggleNotificationRead(request, notification_id):
    if not request.user.is_authenticated or not hasattr(request.user, 'member'):
        return redirect('notifications')

    if request.method != "POST":
        return redirect('notifications')

    member = request.user.member
    notification = get_object_or_404(Notification, pk=notification_id, member=member)

    action = request.POST.get('action')
    notification.is_read = action != 'mark_unread'
    notification.save(update_fields=['is_read'])

    next_page = request.POST.get('next')
    if next_page == 'detail':
        return redirect('recieveNotification', notification_id=notification.notification_id)

    return redirect('notifications')


@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def PaymentView(request, transaction_id):
    transaction_obj=get_object_or_404(Transaction,pk=transaction_id)
    
    # Calculate overdue days
    loan = transaction_obj.loan
    overdue_days = 0
    if loan.return_date:
        delta = loan.return_date - loan.due_date
        overdue_days = max(delta.days, 0)
    else: 
        delta = timezone.now().date() - loan.due_date
        overdue_days = max(delta.days, 0)
        
    fine_amount = transaction_obj.amount
    
    if request.method=="POST":
        # Process payment (mock for now or update status)
        with db_transaction.atomic():
            transaction_obj.status = "PAID"
            transaction_obj.save()

            
            # Since fine is paid, if loan was overdue, maybe update loan status to RETURNED if it was returned but fine pending?
            # Or just leave it. Assuming payment means fine is settled.
            
        return redirect('fine_success_detail', transaction_id=transaction_obj.transaction_id)
        
    return render(request, 'lmsApp/transaction pages/paymentform.html', {
        'transaction': transaction_obj,
        'fine_amount': fine_amount,
        'overdue_days': overdue_days
    })

