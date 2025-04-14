from django import forms

from .models import Character


class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = ['name', 'character_class', 'item_level', 'roster_level', 'is_main']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'character_class': forms.Select(attrs={'class': 'form-select'}),
            'item_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'is_gold_earner': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
