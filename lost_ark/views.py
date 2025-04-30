import logging

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView

from .forms import CharacterForm, WeeklyContentForm
from .mixins import UserOwnershipMixin
from .models import Character, CharacterWeeklyContent, CompletedGate, WeeklyContent, get_current_week


def home(request):
    return render(request, 'lost_ark/index.html')


def permission_denied_view(request, exception=None):
    return render(request, 'lost_ark/403.html', status=403)


# -----------------CHARACTER VIEWS------------------#

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

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.user_can_access(self.request.user):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the 'next' URL from GET or fallback to the referer
        context['next'] = self.request.GET.get('next') or self.request.META.get('HTTP_REFERER', '/')
        return context

    def get_success_url(self):
        # Return the 'next' parameter from the form POST or fallback to HTTP_REFERER
        return self.request.POST.get('next') or self.request.META.get('HTTP_REFERER', '/')


class CharacterDeleteView(UserOwnershipMixin, DeleteView):
    model = Character
    template_name = 'lost_ark/characters/confirm_delete.html'
    success_url = reverse_lazy('lost_ark:character_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.user_can_access(self.request.user):
            raise PermissionDenied
        return obj


# -----------------WEEKLY CONTENT VIEWS------------------#


class WeeklyContentTableView(TemplateView):
    template_name = 'lost_ark/weekly_content/content_table.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        characters = Character.objects.filter(user=user)[:6]
        raids = WeeklyContent.objects.all()

        characters_with_weekly_content = []
        total_gold_earned = 0
        total_possible_gold = 0

        for character in characters:
            character_weekly_contents = CharacterWeeklyContent.objects.filter(character=character)

            weekly_contents_data = []
            for weekly_content in character_weekly_contents:
                total_gold = sum(gate.gold_amount for gate in weekly_content.weekly_content.gates.all())
                gold_earned = weekly_content.gold_earned()

                # Get gate numbers (assuming gates start from 1)
                gate_numbers = [gate.number for gate in weekly_content.weekly_content.gates.all() if gate.number > 1]

                # Prepare all status options with their properties
                all_status_options = []

                # Add Gate options
                for gate_num in gate_numbers:
                    all_status_options.append({
                        'value': f"Gate {gate_num}",
                        'label': f"Gate {gate_num}",
                        'color': "#ffc107",  # Yellow
                        'selected': weekly_content.status == f"Gate {gate_num}",
                    })

                # Add "Completed" and "Not Done" options
                all_status_options.extend([
                    {
                        'value': "Completed",
                        'label': "Completed",
                        'color': "#28a745",  # Green
                        'selected': weekly_content.status.lower() == "completed",
                    },
                    {
                        'value': "Not Done",
                        'label': "Not Done",
                        'color': "#dc3545",  # Red
                        'selected': weekly_content.status.lower() == "not done",
                    }
                ])

                # Custom sorting:
                # 1. Completed first
                # 2. Gates in descending order (3 before 2)
                # 3. Not Done last
                all_status_options.sort(key=lambda x: (
                    x['label'] != 'Completed',  # False (0) comes before True (1)
                    -int(x['label'].split()[1]) if x['label'].startswith('Gate') else 0,  # Negative for descending
                    x['label'] != 'Not Done',  # Not Done gets higher value

                ))

                weekly_contents_data.append({
                    'weekly_content': weekly_content.weekly_content,
                    'difficulty': weekly_content.weekly_content.difficulty,
                    'status': weekly_content.status,
                    'gold_earned': gold_earned,
                    'total_gold': total_gold,
                    'form': WeeklyContentForm(instance=weekly_content),
                    'id': weekly_content.id,
                    'gate_numbers': gate_numbers,
                    'sorted_status_options': all_status_options,  # Pass the sorted options to template
                })

                # Accumulate gold totals
                total_gold_earned += gold_earned
                total_possible_gold += total_gold

            characters_with_weekly_content.append({
                'character': character,
                'weekly_contents': weekly_contents_data,
                'can_add_raid': 3 > character_weekly_contents.count() >= 0,
            })

        return {
            'characters_with_weekly_content': characters_with_weekly_content,
            'raids': raids,
            'total_gold_earned': total_gold_earned,
            'total_possible_gold': total_possible_gold,
        }


class WeeklyStatusUpdateView(View):
    def post(self, request, *args, **kwargs):
        weekly_content_id = request.POST.get('weekly_content_id')
        status = request.POST.get('status')
        character_id = request.POST.get('character_id')

        if not all([weekly_content_id, status, character_id]):
            messages.error(request, "Missing required parameters")
            print("Missing parameters")  # Debug
            return redirect('lost_ark:weekly_content_table')

        try:
            weekly_content = CharacterWeeklyContent.objects.get(
                id=weekly_content_id,
                character_id=character_id
            )

            # Normalize status
            status = status.replace('_', ' ').title()  # Handles both "gate_2" and "Gate 2"

            weekly_content.status = status
            weekly_content.save()

            total_gates = weekly_content.weekly_content.gates.count()
            completed_gate_count = weekly_content.completed_gate_entries.count()

            if status == 'Not Done':
                self.delete_completed_gate(weekly_content, 0)
            else:
                self.handle_gate_creation_or_deletion(
                    weekly_content,
                    completed_gate_count,
                    total_gates,
                    status
                )

            messages.success(request, f"Status updated to {status.replace('_', ' ').title()}")
            return redirect('lost_ark:weekly_content_table')

        except CharacterWeeklyContent.DoesNotExist as e:
            print(f"Error: {str(e)}")  # Debug
            messages.error(request, "Weekly content not found")
        except Exception as e:
            print(f"Error: {str(e)}")  # Debug
            messages.error(request, f"Error updating status: {str(e)}")

        return redirect('lost_ark:weekly_content_table')

    def handle_gate_creation_or_deletion(self, character_weekly_content, completed_gate_count, total_gates, status):
        if status.startswith('Gate '):
            gate_num = int(status.split(' ')[1])
            gate_number = gate_num - 1  # Assuming gate numbers start from 2
        elif status == 'Completed':
            gate_number = total_gates
        else:
            return

        if completed_gate_count < gate_number:
            self.create_completed_gate(character_weekly_content, gate_number)
        elif completed_gate_count > gate_number:
            self.delete_completed_gate(character_weekly_content, gate_number)

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


class WeeklyContentAddView(View):
    def post(self, request, *args, **kwargs):
        character_id = request.POST.get('character_id')
        raid_id = request.POST.get('raid_id')

        if not character_id or not raid_id:
            messages.error(request, "Missing character or raid selection.")
            return redirect('lost_ark:weekly_content_table')

        try:
            character = Character.objects.get(id=character_id, user=request.user)
            weekly_content = WeeklyContent.objects.get(id=raid_id)

            if CharacterWeeklyContent.objects.filter(character=character, weekly_content=weekly_content).exists():
                messages.error(request, f"{weekly_content.name} already added for {character.name}.")
                return redirect('lost_ark:weekly_content_table')
            elif character.item_level < weekly_content.min_ilvl:
                messages.error(request, "Character's Item level too low for this raid.")
                return redirect('lost_ark:weekly_content_table')

            new_content = CharacterWeeklyContent(
                character=character,
                weekly_content=weekly_content,
                week=get_current_week(),
                status='Not Done'
            )
            new_content.save()

            messages.success(request, f"{weekly_content.name} successfully added for {character.name}.")

        except Character.DoesNotExist:
            messages.error(request, "Character not found.")
        except WeeklyContent.DoesNotExist:
            messages.error(request, "Raid not found.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('lost_ark:weekly_content_table')


class WeeklyContentRemoveView(View):
    def post(self, request, *args, **kwargs):
        character_id = request.POST.get('character_id')
        raid_id = request.POST.get('raid_id')

        if not character_id or not raid_id:
            messages.error(request, "Missing character or raid selection.")
            return redirect('lost_ark:weekly_content_table')

        try:
            character = Character.objects.get(id=character_id, user=request.user)
            weekly_content = WeeklyContent.objects.get(id=raid_id)

            assignment = CharacterWeeklyContent.objects.filter(
                character=character,
                weekly_content=weekly_content,
                week=get_current_week()
            ).first()

            if not assignment:
                messages.error(request, f"{weekly_content.name} is not assigned to {character.name} this week.")
                return redirect('lost_ark:weekly_content_table')

            assignment.delete()
            messages.success(request, f"{weekly_content.name} successfully removed for {character.name}.")

        except Character.DoesNotExist:
            messages.error(request, "Character not found.")
        except WeeklyContent.DoesNotExist:
            messages.error(request, "Raid not found.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('lost_ark:weekly_content_table')
