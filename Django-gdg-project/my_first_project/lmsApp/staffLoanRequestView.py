from django.shortcuts import render,redirect, get_object_or_404
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import TemplateHTMLRenderer,JSONRenderer
from .form import LoanRequestForm,PaymentForm
from .models import LoanRequest,Book,Loan,Member,Notification, Transaction
from .serrializer import LoanRequestSerializer,TransactionSerializer
from .orm_queries import member_has_overdue_loans

@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def staffLoanRequestViewList(request):
    if request.method=="GET":
        status_filter=request.GET.get('status')

        loans=LoanRequest.objects.select_related('member','book') \
            .order_by('-created_at')
        
        # Apply status filter when provided to keep list predictable.
        if status_filter and status_filter != "ALL":
            loans=loans.filter(status=status_filter)
        
        if request.accepted_renderer.format=="html":
            return Response(
                {'loans':loans,
                'current_status': status_filter or "ALL"
                },
                template_name="lmsApp/loan pages/staff_loan_request_list.html"
            )
        
        else:
            serializer=LoanRequestSerializer(loans,many=True)
            return Response(serializer.data,status=status.HTTP_200_OK)

@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def staffLoanRequestViewDetail(request,loan_request_id):
    
    loan_request=get_object_or_404(LoanRequest.objects.select_related('member', 'book', 'loan'),pk=loan_request_id)
    
    # Check for any unpaid transactions associated with this loan request
    unpaid_transaction = None
    if loan_request.loan:
        unpaid_transaction = loan_request.loan.transactions.filter(status="UNPAID").first()
    
    if request.method=="GET":
        if request.accepted_renderer.format=="html":
            return Response(
                {
                    'loan_request': loan_request,
                    'unpaid_transaction': unpaid_transaction
                },
                template_name="lmsApp/loan pages/staff_loan_request_detail.html"
            )
        else:
            serializer=LoanRequestSerializer(loan_request)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def staffLoanRequestViewApprove(request,loan_request_id):
  
    loan_request=get_object_or_404(LoanRequest,pk = loan_request_id)

    if request.method=="POST":
        if loan_request.status != "PENDING":
            return Response(
                {'error':"Only pending requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST
            )
        with db_transaction.atomic():
            loan_request.status = "APPROVED"

            now=timezone.now()
            pickup_until=now + timezone.timedelta(days=3)
            loan_request.pickup_until = pickup_until # Also save the calculated date
            loan_request.approved_at = now

            loan_request.save()


        send_notification_logic(loan_request)

        if request.accepted_renderer.format == "html":
            return redirect("loan_request_detail",loan_request_id)

        else:
            serializer=LoanRequestSerializer(loan_request)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def staffLoanRequestViewReject(request,loan_request_id):
  
    loan_request=get_object_or_404(LoanRequest,pk = loan_request_id)

    if request.method=="POST":
        if loan_request.status != "PENDING":
            return Response(
                {'error':"Only pending requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST
            )
        with db_transaction.atomic():
            loan_request.status = "REJECTED"
            loan_request.save()

        send_notification_logic(loan_request)

        if request.accepted_renderer.format == "html":
            return redirect("loan_request_detail",loan_request_id)

        else:
            serializer=LoanRequestSerializer(loan_request)
            return Response(serializer.data,status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@renderer_classes([TemplateHTMLRenderer, JSONRenderer])
def FineTransactionView(request, transaction_id):

    fine_transaction = get_object_or_404(Transaction, pk=transaction_id)
    loan = fine_transaction.loan

    overdue_loans = member_has_overdue_loans(fine_transaction.member)

    if not overdue_loans:
        if request.accepted_renderer.format == "html":
            return redirect('no_overdue')
        return Response(
            {"detail": "No overdue loans found."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Mark loan overdue before calculating fine to keep status consistent.
    loan.status = "OVERDUE"
    loan.save()

    # 🔢 Calculate fine
    today = timezone.now()
    due_date = fine_transaction.due_date
    overdue_days = max((today - due_date).days, 0)
    fine_amount = overdue_days * fine_transaction.daily_rate

    if request.method == "POST":

        payment_form = PaymentForm(
            request.POST,
            instance=fine_transaction
        )

        if payment_form.is_valid():

            transaction = payment_form.save(commit=False)

            # 🔐 enforce correct fine amount
            transaction.amount = fine_amount
            transaction.save()

            # 🔔 Send notification for fine payment
            try:
                loan_req_obj = transaction.loan.loan_requests_loan  # Access LoanRequest via OneToOne related_name
                notif_message = (
                    f"Fine payment received for overdue loan '{loan_req_obj.book.title}'. "
                    f"Amount Paid: {transaction.amount} (Daily Rate: {transaction.daily_rate})."
                )
                Notification.objects.create(
                    member=transaction.member,
                    loan_request=loan_req_obj,
                    message=notif_message
                )
            except Exception as e:
                # Fallback if loan request link is missing or other issue
                pass

            if request.accepted_renderer.format == "html":
                return redirect('fine_success')

            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # ❌ Form errors
        if request.accepted_renderer.format == "html":
            return Response(
                {
                    'payment_form': payment_form,
                    'transaction': fine_transaction,
                    'fine_amount': fine_amount,
                    'overdue_days': overdue_days
                },
                template_name='lmsApp/transaction pages/paymentform.html'
            )

        return Response(
            payment_form.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔵 GET Request
    payment_form = PaymentForm(
        instance=fine_transaction,
        initial={'amount': fine_amount}
    )

    if request.accepted_renderer.format == "html":
        return Response(
            {
                'payment_form': payment_form,
                'fine_amount': fine_amount,
                'overdue_days': overdue_days,
                'transaction': fine_transaction
            },
            template_name='lmsApp/transaction pages/paymentform.html'
        )

    serializer = TransactionSerializer(fine_transaction)
    return Response(
        {
            "transaction": serializer.data,
            "fine_amount": fine_amount,
            "overdue_days": overdue_days
        }
    )

def send_notification_logic(loan_request, notification_id=None):
    # If the first argument happens to be 'request' (HttpRequest), ignore it and use the second.
    # But since I changed the call sites, let's just use loan_request.
    
    message = None
    if loan_request.status == "APPROVED":
        pickup_msg = ""
        if loan_request.pickup_until:
             pickup_msg = f" Please pick it up until {loan_request.pickup_until.strftime('%Y-%m-%d')}."
        
        message = f"Your loan request for '{loan_request.book.title}' has been approved.{pickup_msg}"
        
    elif loan_request.status == "REJECTED":
        message = f"Your loan request for '{loan_request.book.title}' has been rejected."
        
    elif loan_request.status == "EXPIRED":
        message = f"Your approved loan request for '{loan_request.book.title}' has expired because it was not picked up."
    
    if message:
        Notification.objects.create(
            member=loan_request.member,
            loan_request=loan_request,
            message=message
        )

@api_view(['GET'])
@renderer_classes([JSONRenderer])
def get_approved_loan_duration(request):
    """
    API for Django Admin: Fetch the duration of an APPROVED loan request for a Book+Member pair.
    """
    member_id = request.GET.get('member_id')
    book_id = request.GET.get('book_id')
    
    if not member_id or not book_id:
        return Response({'error': 'Missing member_id or book_id'}, status=400)
        
    request_obj = LoanRequest.objects.filter(
        member_id=member_id,
        book_id=book_id,
        status='APPROVED',
        loan__isnull=True
    ).first()
    
    if request_obj:
        return Response({
            'found': True,
            'duration_days': request_obj.requested_duration
        })
    else:
        return Response({'found': False, 'duration_days': None})
