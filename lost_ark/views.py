import logging

logger = logging.getLogger(__name__)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import CharacterForm
from .mixins import UserOwnershipMixin
from .models import Character


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


from django.views.generic import TemplateView
from .models import WeeklyContent
from .forms import WeeklyContentForm


class WeeklyContentTableView(TemplateView):
    template_name = 'lost_ark/weekly_content/content_table.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        characters = Character.objects.filter(user=user)[:6]
        raids = WeeklyContent.objects.all()

        characters_with_weekly_content = []

        for character in characters:
            character_weekly_contents = CharacterWeeklyContent.objects.filter(character=character)

            weekly_contents_data = []
            for weekly_content in character_weekly_contents:
                total_gold = sum(gate.gold_amount for gate in weekly_content.weekly_content.gates.all())
                gold_earned = weekly_content.gold_earned()

                weekly_contents_data.append({
                    'weekly_content': weekly_content.weekly_content,
                    'difficulty': weekly_content.weekly_content.difficulty,
                    'status': weekly_content.status,
                    'gold_earned': gold_earned,
                    'total_gold': total_gold,
                    'form': WeeklyContentForm(instance=weekly_content),
                    'id': weekly_content.id,
                    'gate_numbers': [gate.number for gate in weekly_content.weekly_content.gates.all() if
                                     gate.number > 1],
                })

            characters_with_weekly_content.append({
                'character': character,
                'weekly_contents': weekly_contents_data,
                'can_add_raid': character_weekly_contents.count() < 3
            })

        return {
            'characters_with_weekly_content': characters_with_weekly_content,
            'raids': raids,
        }

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get('form_type')

        if form_type == 'update_status':
            weekly_content_id = request.POST.get('weekly_content_id')
            status = request.POST.get('status')

            if not weekly_content_id or not status:
                return self.render_to_response(self.get_context_data(error='Missing data'))

            try:
                weekly_content = CharacterWeeklyContent.objects.get(id=weekly_content_id)
                weekly_content.status = status
                weekly_content.save()

                # Logic to handle gates (similar to the admin logic)
                weekly_content_obj = weekly_content.weekly_content
                total_gates = weekly_content_obj.gates.count()
                completed_gate_count = weekly_content.completed_gate_entries.count()

                if status == 'Not Done':
                    self.delete_completed_gate(weekly_content, 0)
                elif status != 'Not Done':
                    self.handle_gate_creation_or_deletion(weekly_content, completed_gate_count, total_gates, status)

                return redirect('lost_ark:weekly_content_table')  # redirect to prevent form resubmission on refresh
            except CharacterWeeklyContent.DoesNotExist:
                return self.render_to_response(self.get_context_data(error='Content not found'))

        # Handle other forms (like adding a raid)
        return self.render_to_response(self.get_context_data(error='Invalid action'))

    def handle_gate_creation_or_deletion(self, character_weekly_content, completed_gate_count, total_gates, status):
        gate_mapping = {
            'Gate 2': 1,
            'Gate 3': 2,
            'Gate 4': 3,
            'Completed': total_gates
        }

        if status in gate_mapping:
            gate_number = gate_mapping[status]
            if completed_gate_count < gate_number:
                self.create_completed_gate(character_weekly_content, gate_number)
            elif completed_gate_count > gate_number:
                self.delete_completed_gate(character_weekly_content, gate_number - 1)

    def create_completed_gate(self, character_weekly_content, gate_number):
        # Loop to create gates up to the given gate_number
        for i in range(1, gate_number + 1):
            if not character_weekly_content.completed_gate_entries.filter(gate__number=i).exists():
                gate = character_weekly_content.weekly_content.gates.filter(number=i).first()
                if gate:
                    CompletedGate.objects.create(
                        character_weekly_content=character_weekly_content,
                        gate=gate
                    )
                    character_weekly_content.update_status()
                    character_weekly_content.save()

    def delete_completed_gate(self, character_weekly_content, gate_number):
        # Loop through gates starting from the highest down to the given gate_number
        for i in range(character_weekly_content.weekly_content.gates.count(), gate_number, -1):
            completed_gate = character_weekly_content.completed_gate_entries.filter(gate__number=i).first()
            if completed_gate:
                completed_gate.delete()
                character_weekly_content.update_status()
                character_weekly_content.save()


from django.views import View
from django.shortcuts import redirect
from .models import CharacterWeeklyContent, CompletedGate


class update_weekly_status(View):
    def post(self, request, *args, **kwargs):
        weekly_content_id = request.POST.get('weekly_content_id')
        status = request.POST.get('status')

        if not weekly_content_id or not status:
            return redirect('lost_ark:weekly_content_table')

        try:
            weekly_content = CharacterWeeklyContent.objects.get(id=weekly_content_id)
            weekly_content.status = status
            weekly_content.save()

            total_gates = weekly_content.weekly_content.gates.count()
            completed_gate_count = weekly_content.completed_gate_entries.count()

            if status == 'Not Done':
                self.delete_completed_gate(weekly_content, 0)
            else:
                self.handle_gate_creation_or_deletion(weekly_content, completed_gate_count, total_gates, status)

        except CharacterWeeklyContent.DoesNotExist:
            pass  # Optional: log error or add a message

        return redirect('lost_ark:weekly_content_table')

    def handle_gate_creation_or_deletion(self, character_weekly_content, completed_gate_count, total_gates, status):
        gate_mapping = {
            'Gate 2': 1,
            'Gate 3': 2,
            'Gate 4': 3,
            'Completed': total_gates
        }

        if status in gate_mapping:
            gate_number = gate_mapping[status]
            if completed_gate_count < gate_number:
                self.create_completed_gate(character_weekly_content, gate_number)
            elif completed_gate_count > gate_number:
                self.delete_completed_gate(character_weekly_content, gate_number - 1)

    def create_completed_gate(self, character_weekly_content, gate_number):
        for i in range(1, gate_number + 1):
            if not character_weekly_content.completed_gate_entries.filter(gate__number=i).exists():
                gate = character_weekly_content.weekly_content.gates.filter(number=i).first()
                if gate:
                    CompletedGate.objects.create(
                        character_weekly_content=character_weekly_content,
                        gate=gate
                    )
        character_weekly_content.update_status()
        character_weekly_content.save()

    def delete_completed_gate(self, character_weekly_content, gate_number):
        for i in range(character_weekly_content.weekly_content.gates.count(), gate_number, -1):
            completed_gate = character_weekly_content.completed_gate_entries.filter(gate__number=i).first()
            if completed_gate:
                completed_gate.delete()
        character_weekly_content.update_status()
        character_weekly_content.save()
