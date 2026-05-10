from django.shortcuts import render,redirect
from django.utils import timezone
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer,JSONRenderer
from rest_framework.exceptions import NotFound
from .models import Book,Member,LoanRequest,Loan
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from .serrializer import BookSerializer,LoanSerializer
from .form import BookForm


def _is_staff_or_admin(user):
    if not user.is_authenticated:
        return False
    return (
        getattr(user, "role", None) in {"staff", "admin"}
        or user.is_staff
        or user.is_superuser
    )


def _deny_if_not_staff_or_admin(request):
    if _is_staff_or_admin(request.user):
        return None
    if request.accepted_renderer.format == "html":
        return redirect("login")
    return Response(
        {"detail": "Staff or admin access required."},
        status=status.HTTP_403_FORBIDDEN,
    )

# Create your views here.
# def home(request):
#     return render(request,'lmsApp/home.html')

@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def book_list(request):
    books=Book.objects.all()
    # Track books where the current member cannot re-apply yet.
    member = None
    if request.user.is_authenticated and hasattr(request.user, 'member'):
        member = request.user.member

    applied_book_ids = []
    
    if member:
        # Disable apply when there is a pending/approved request for the same book.
        pending_or_approved_request_book_ids = LoanRequest.objects.filter(
            member=member
        ).filter(status__in=['PENDING', 'APPROVED']).values_list('book_id', flat=True)

        # Disable apply while any loan for the same book is still active/overdue.
        active_loan_book_ids = Loan.objects.filter(member=member).exclude(
            status='RETURNED'
        ).values_list('book_id', flat=True)
        
        applied_book_ids = list(set(pending_or_approved_request_book_ids) | set(active_loan_book_ids))

    serializer=BookSerializer(books,many=True)

    if request.accepted_renderer.format=="json":
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    return Response(
        {'books': books, 'applied_book_ids': applied_book_ids},
        template_name='lmsApp/book pages/book_list.html'
    )
    
@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def book_details(request,book_id):
    try:
        book=Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        raise NotFound("Book Not Found")
    
    serializer=BookSerializer(book)

    if request.accepted_renderer.format=="json":
        return Response(serializer.data)
    
    return Response(
        {'book':book},
        template_name='lmsApp/book pages/book_detail.html'
    )

@api_view(['POST','GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def AddBook(request):
    access_denied = _deny_if_not_staff_or_admin(request)
    if access_denied:
        return access_denied
    if request.method=="POST":
        if request.accepted_renderer.format=="html":
            form=BookForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('book_list')
            else:
                return Response({'form':form},template_name="lmsApp/book pages/book_form.html",status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer=BookSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'data':serializer.data},status=status.HTTP_201_CREATED,
            )
    else:
        if request.accepted_renderer.format=="html":
            form=BookForm()
            return Response({'form':form},template_name='lmsApp/book pages/book_form.html')
        
        serializer=BookSerializer()
        return Response(serializer.data)

@api_view(['PATCH','PUT','POST','GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def UpdateBook(request,book_id):
    access_denied = _deny_if_not_staff_or_admin(request)
    if access_denied:
        return access_denied
    try:
        book=Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        raise NotFound("Book Not Found")
    
    if request.method in ["PUT","POST"]:
        if request.accepted_renderer.format=="html":
            form=BookForm(request.POST,instance=book)
            if form.is_valid():
                form.save()
                return redirect('book_list')
            else:
                return Response({'form':form},template_name='lmsApp/book pages/book_form.html',status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer=BookSerializer(book,data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'data':serializer.data},status=status.HTTP_200_OK)
    
    elif request.method=="PATCH":
        if request.accepted_renderer.format=="html":
            form=BookForm(request.POST,instance=book)
            if form.is_valid():
                form.save()
                return redirect('book_list')
            else:
                return Response({'form':form},template_name='lmsApp/book pages/book_form.html',status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer=BookSerializer(book,data=request.data,partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'data':serializer.data},status=status.HTTP_200_OK)
    else:
        if request.accepted_renderer.format=="html":
            form=BookForm(instance=book)
            return Response({'form':form},template_name="lmsApp/book pages/book_form.html")
        serializer=BookSerializer(book)
        return Response(serializer.data)

@api_view(['DELETE','GET','POST'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def DeleteBook(request,book_id):
    access_denied = _deny_if_not_staff_or_admin(request)
    if access_denied:
        return access_denied
    try:
        book=Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        raise NotFound("Book Not Found")
    
    if request.method in ["DELETE", "POST"]:
        try:
            book.delete()
        except ProtectedError:
            if request.accepted_renderer.format == "html":
                return Response(
                    {
                        "book": book,
                        "error": "Cannot delete this book because it has active or past loans.",
                    },
                    template_name="lmsApp/book pages/confrim_delete.html",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "detail": "Cannot delete this book because it has related loans.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        
        if request.accepted_renderer.format == "html":
            return redirect('book_list')
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    if request.accepted_renderer.format=="html":
        return Response(
            {'book': book},
            template_name="lmsApp/book pages/confrim_delete.html"
        )

    serializer=BookSerializer(book)
    return Response(serializer.data,status=status.HTTP_200_OK)


class loanMgtView(APIView):
   
    def post(self,request,book_id,member_id):

        try:
            book=Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return Response({"error":"Book not found"},status=status.HTTP_404_NOT_FOUND)
        
        try:
            member=Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return Response({"error":"Member not found"},status=status.HTTP_404_NOT_FOUND)
        
        today=timezone.now().date()

        # Block new loans if any active loans are overdue.
        active_loans=member.loans.filter(return_date__isnull=True)
        overdue_loans=[loan for loan in active_loans if loan.is_overdue]

        if overdue_loans:
            return Response({"error":"Member has overdue loans. Can not issue new book."},status=status.HTTP_400_BAD_REQUEST)
        
        if book.available_copies <= 0:
            return Response({"error":"No available copies for this book."},status=status.HTTP_400_BAD_REQUEST)
        
       
        serializer=LoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(book=book,member=member,return_date=today+timezone.timedelta(days=7))
        return Response(serializer.data,status=status.HTTP_201_CREATED)

