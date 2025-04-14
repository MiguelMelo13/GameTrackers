from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

class UserOwnershipMixin(LoginRequiredMixin):
    """Verify that the current user owns the object"""
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.user_can_access(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)