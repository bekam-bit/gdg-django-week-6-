from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required

from .form import RegisterForm

from .decorators import role_required

ROLE_LABELS = {
    "member": "Member",
    "staff": "Staff",
    "admin": "Admin",
}


def _redirect_by_role(user):
    # Centralize dashboard routing to keep login views consistent.
    if user.role == "admin" or user.is_superuser:
        return redirect("admin_dashboard")
    if user.role == "staff" or user.is_staff:
        return redirect("staff_dashboard")
    if user.role == "member":
        return redirect("member_dashboard")
    return redirect("login")


def _render_login(request, role=None, role_label="Account", error=None):
    # Single renderer for all login flows to keep templates/contexts aligned.
    context = {"role_label": role_label}
    if role:
        context["role"] = role
    if error:
        context["error"] = error
    return render(request, "lmsApp/auth_pages/login_role.html", context)

def homeRoleView(request):
    return render(request, 'lmsApp/home.html')

 
def registerView(request):
    if request.method == "POST":
        Form = RegisterForm(request.POST)
        if Form.is_valid():
            member = Form.save()
            login(request,member.user)
            return redirect('member_dashboard')
    else:
        Form = RegisterForm()
    
    return render(request, 'lmsApp/auth_pages/register.html', {'form': Form})

def loginView(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return _redirect_by_role(user)

        return _render_login(request, error="Invalid credentials")

    return _render_login(request)

def loginRoleView(request, role):
    role = role.lower()
    if role not in ROLE_LABELS:
        return redirect('login')

    role_label = ROLE_LABELS[role]

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if role == "staff" and not (user.role == "staff" or user.is_staff):
                return _render_login(
                    request,
                    role=role,
                    role_label=role_label,
                    error=f"This account is not a {role_label} account.",
                )
            if role == "admin" and not (user.role == "admin" or user.is_superuser):
                return _render_login(
                    request,
                    role=role,
                    role_label=role_label,
                    error=f"This account is not a {role_label} account.",
                )
            if role == "member" and user.role != "member":
                return _render_login(
                    request,
                    role=role,
                    role_label=role_label,
                    error=f"This account is not a {role_label} account.",
                )

            login(request, user)
            return _redirect_by_role(user)

        return _render_login(request, role=role, role_label=role_label, error="Invalid credentials")

    return _render_login(request, role=role, role_label=role_label)

def logoutView(request):
    logout(request)
    return redirect('login')

@login_required
@role_required(['staff','admin'])
def staffDashboard(request):
    return render(request, 'lmsApp/staffDashBoard.html')

@login_required
@role_required(allowed_roles=['member'])
def memberDashboard(request):
    return render(request, 'lmsApp/memberDashBoard.html')

@login_required
@role_required(allowed_roles=['admin'])
def adminDashboard(request):
    return render(request, 'lmsApp/adminDashBoard.html')
