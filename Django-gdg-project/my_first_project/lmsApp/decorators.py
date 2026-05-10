from django.shortcuts import redirect

def role_required(allowed_roles=['admin','staff','member']):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                if request.user.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
                if request.user.is_superuser and ("admin" in allowed_roles or "staff" in allowed_roles):
                    return view_func(request, *args, **kwargs)
                if request.user.is_staff and "staff" in allowed_roles:
                    return view_func(request, *args, **kwargs)
            
            return redirect('login') # or some other fallback
        return _wrapped_view
    return decorator