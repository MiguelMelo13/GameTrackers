from django import forms

from .models import Character, CharacterWeeklyContent


class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = ['name', 'character_class', 'item_level', 'roster_level', 'is_main', 'is_gold_earner']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'character_class': forms.Select(attrs={'class': 'form-select'}),
            'item_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'is_gold_earner': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WeeklyContentForm(forms.ModelForm):
    class Meta:
        model = CharacterWeeklyContent
        fields = ['status']  # Only allow the status field to be updated via this form

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget = forms.Select(choices=CharacterWeeklyContent.STATUS_CHOICES)
