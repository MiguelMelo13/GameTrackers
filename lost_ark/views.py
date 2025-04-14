from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import CharacterForm
from .mixins import UserOwnershipMixin
from .models import Character, WeeklyContent


def home(request):
    return render(request, 'lost_ark/index.html')


def permission_denied_view(request, exception=None):
    return render(request, 'lost_ark/403.html', status=403)


class CharacterListView(LoginRequiredMixin, ListView):
    model = Character
    template_name = 'lost_ark/characters/list.html'
    context_object_name = 'characters'


def get_queryset(self):
    # Only show characters belonging to the current user
    return Character.objects.filter(user=self.request.user)


class CharacterCreateView(LoginRequiredMixin, CreateView):
    model = Character
    form_class = CharacterForm
    template_name = 'lost_ark/characters/form.html'
    success_url = reverse_lazy('lost_ark:character_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CharacterUpdateView(UserOwnershipMixin, UpdateView):
    model = Character
    form_class = CharacterForm
    template_name = 'lost_ark/characters/form.html'
    success_url = reverse_lazy('lost_ark:character_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.user_can_access(self.request.user):
            raise PermissionDenied
        return obj


class CharacterDeleteView(UserOwnershipMixin, DeleteView):
    model = Character
    template_name = 'lost_ark/characters/confirm_delete.html'
    success_url = reverse_lazy('lost_ark:character_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.user_can_access(self.request.user):
            raise PermissionDenied
        return obj


class WeeklyContentTableView(LoginRequiredMixin, ListView):
    model = WeeklyContent  # Replace with the correct model for weekly content
    template_name = 'lost_ark/weekly_content/weekly_content_table.html'
    context_object_name = 'weekly_content_list'

    def get_queryset(self):
        """
        Override to filter the weekly content by the current user's profile or other criteria
        if necessary.
        """
        return WeeklyContent.objects.all()  # You can filter this queryset to display only the content relevant to the user
