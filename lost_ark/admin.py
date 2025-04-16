from django.contrib import admin

from .models import Character, WeeklyContent, Gate, CharacterWeeklyContent, CompletedGate


# ---------------------------- CHARACTER ADMIN ----------------------------

class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'character_class', 'item_level', 'is_main', 'is_gold_earner', 'roster_level', 'user')
    list_filter = ('character_class', 'is_main', 'is_gold_earner', 'user')
    search_fields = ('name', 'user__username', 'character_class')
    ordering = ['user', '-is_main', 'name']
    list_per_page = 20

    def save_model(self, request, obj, form, change):
        # Check if the user already has 6 gold earners
        if obj.is_gold_earner:
            is_gold_earner_count = Character.objects.filter(user=obj.user, is_gold_earner=True).count()
            if is_gold_earner_count >= 6 and not change:
                raise ValueError(
                    "A user can have no more than 6 gold earners. Untick another character to make this one a gold earner.")
        super().save_model(request, obj, form, change)


# ---------------------------- WEEKLY CONTENT ADMIN ----------------------------

class WeeklyContentAdmin(admin.ModelAdmin):
    list_display = ('name', 'difficulty', 'min_ilvl', 'is_default')
    list_filter = ('difficulty', 'is_default')
    search_fields = ('name',)
    ordering = ['-is_default', 'name']
    list_per_page = 20


# ---------------------------- GATE ADMIN ----------------------------

class GateAdmin(admin.ModelAdmin):
    list_display = ('weekly_content', 'number', 'gold_amount', 'cooldown_weeks')
    list_filter = ('weekly_content',)
    search_fields = ('weekly_content__name',)
    ordering = ['weekly_content', 'number']
    list_per_page = 20


# ---------------------------- CHARACTER WEEKLY CONTENT ADMIN ----------------------------

class CharacterWeeklyContentAdmin(admin.ModelAdmin):
    list_display = ('character', 'weekly_content', 'week', 'status', 'gold_earned')
    list_filter = ('weekly_content', 'character', 'status')
    search_fields = ('character__name', 'weekly_content__name')
    ordering = ['character', '-week']
    list_per_page = 20

    def gold_earned(self, obj):
        return obj.gold_earned()

    gold_earned.short_description = 'Gold Earned'

    def save_model(self, request, obj, form, change):
        """
        Save the model and handle the creation or deletion of CompletedGate objects.
        """
        # Call the original save method to save the CharacterWeeklyContent object
        super().save_model(request, obj, form, change)

        # Retrieve the WeeklyContent and Gates associated with the CharacterWeeklyContent
        weekly_content = obj.weekly_content
        total_gates = weekly_content.gates.count()
        completed_gate_count = obj.completed_gate_entries.count()

        # Avoid unnecessary repeated count check
        if obj.status == 'Not Done':
            self.delete_completed_gate(obj, 0)
        elif obj.status != 'Not Done':
            self.handle_gate_creation_or_deletion(obj, completed_gate_count, total_gates)

    def handle_gate_creation_or_deletion(self, obj, completed_gate_count, total_gates):
        """
        Handles the creation or deletion of CompletedGate objects based on status and completion count.
        """
        gate_mapping = {
            'Gate 2': 1,
            'Gate 3': 2,
            'Gate 4': 3,
            'Completed': total_gates
        }

        # Check if status is in gate_mapping
        if obj.status in gate_mapping:
            gate_number = gate_mapping[obj.status]
            if completed_gate_count < gate_number:
                self.create_completed_gate(obj, gate_number)
            elif completed_gate_count > gate_number:
                self.delete_completed_gate(obj, gate_number - 1)

    def create_completed_gate(self, character_weekly_content, gate_number):
        """
        Helper function to create the `CompletedGate` object for the specific gate.
        It ensures that previous gates are created if they haven't been completed yet.
        """
        for i in range(1, gate_number + 1):  # Loop to create gates up to the given gate_number
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
        """
        Helper function to delete the `CompletedGate` objects for the specific gate.
        It ensures that gates are deleted in reverse order, starting from the current gate.
        """
        # Loop through the gates starting from the highest down to the given gate_number
        for i in range(character_weekly_content.weekly_content.gates.count(), gate_number, -1):
            completed_gate = character_weekly_content.completed_gate_entries.filter(gate__number=i).first()
            if completed_gate:
                completed_gate.delete()
                character_weekly_content.update_status()
                character_weekly_content.save()


# ---------------------------- COMPLETED GATE ADMIN ----------------------------

class CompletedGateAdmin(admin.ModelAdmin):
    list_display = ('character_weekly_content', 'gate', 'completed_at')
    list_filter = ('character_weekly_content', 'gate')
    search_fields = ('character_weekly_content__character__name', 'gate__weekly_content__name')
    ordering = ['completed_at']
    list_per_page = 20


# Registering models with admin site

admin.site.register(Character, CharacterAdmin)
admin.site.register(WeeklyContent, WeeklyContentAdmin)
admin.site.register(Gate, GateAdmin)
admin.site.register(CharacterWeeklyContent, CharacterWeeklyContentAdmin)
admin.site.register(CompletedGate, CompletedGateAdmin)
