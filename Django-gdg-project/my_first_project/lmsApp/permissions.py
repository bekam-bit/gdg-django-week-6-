from rest_framework.permissions import BasePermission

class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'staff'

class IsMember(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "member"
