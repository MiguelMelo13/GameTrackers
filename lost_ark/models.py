import datetime

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

DIFFICULTY_CHOICES = [
    ('Normal', 'Normal'),
    ('Hard', 'Hard'),
    ('Hell', 'Hell'),
]

RAID_CHOICES = [

    ('Thaemine', 'Thaemine'),
    ('Echidna', 'Echidna'),
    ('Behemoth', 'Behemoth'),
    ('Aegir (Act 1)', 'Aegir (Act 1)'),
    ('Brelshaza (Act 2)', 'Brelshaza (Act 2)'),
    ('Kazeros (Act 3)', 'Kazeros (Act 3)'),

]

CLASS_CHOICES = [
    ('Berserker', 'Berserker'),  # High-damage melee with burst mode.
    ('Paladin', 'Paladin'),  # Holy warrior, supports or fights at frontline.
    ('Gunlancer', 'Gunlancer'),  # Tanky shield user who protects allies.
    ('Destroyer', 'Destroyer'),  # Hammer wielder with gravity control and CC.
    ('Striker', 'Striker'),  # Agile martial artist with aerial combos.
    ('Wardancer', 'Wardancer'),  # Martial artist storing elemental energy.
    ('Scrapper', 'Scrapper'),  # Balanced brawler with two energy forms.
    ('Soulfist', 'Soulfist'),  # Swaps between melee and ranged with Adamance energy.
    ('Gunslinger', 'Gunslinger'),  # Weapon-swapping sharpshooter, agile and deadly.
    ('Artillerist', 'Artillerist'),  # Burst damage with turrets and tanky style.
    ('Deadeye', 'Deadeye'),  # Triple-wielding brash shooter with versatility.
    ('Sharpshooter', 'Sharpshooter'),  # Bow user with agility and survivability.
    ('Bard', 'Bard'),  # Supportive harp player, excels at healing/buffs.
    ('Sorceress', 'Sorceress'),  # Elemental magic dealer with AoE destruction.
    ('Shadowhunter', 'Shadowhunter'),  # Demon form shapeshifter with enhanced powers.
    ('Deathblade', 'Deathblade'),  # Triple sword assassin with rapid combos.
    ('Reaper', 'Reaper'),  # Burst or sustained DPS with stealth options.
    ('Summoner', 'Summoner'),  # Mage that calls legendary monsters to fight.
    ('Arcana', 'Arcana'),  # Close-range burst mage with fast cooldowns.
    ('Artist', 'Artist'),  # Support who paints holy monsters to heal/buff.
    ('Aeromancer', 'Aeromancer'),  # DPS with weather/umbrella burst mechanics.
    ('Slayer', 'Slayer'),  # Agile melee with easy-to-use burst options.
    ('Machinist', 'Machinist'),  # Drone-using Iron Man-type DPS with zoning tools.
    ('Glavier', 'Glavier'),  # Spear wielder balancing between two stances.
    ('Wild Soul', 'Wild Soul'),  # Yoz specialist with animal transformations and summons.
]


def get_current_week():
    today = now().date()
    return today - datetime.timedelta(days=today.weekday())  # Monday of current week


# ---------------------- CHARACTER MODEL ----------------------


class Character(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=50)
    character_class = models.CharField(max_length=20, choices=CLASS_CHOICES)
    item_level = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(0)])
    roster_level = models.PositiveIntegerField(default=1, validators=[MaxValueValidator(300)])
    is_main = models.BooleanField(default=False)
    is_gold_earner = models.BooleanField(default=False)  # New field added here
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'name')  # Prevent duplicate character names per user
        ordering = ['-is_main', 'name']

    def __str__(self):
        return f"{self.user} - {self.name} ({self.character_class} - {self.item_level})"

    def save(self, *args, **kwargs):
        # Ensure only one main character per user
        if self.is_main:
            Character.objects.filter(user=self.user, is_main=True).exclude(pk=self.pk).update(is_main=False)

        # Ensure no more than 6 gold earners per user
        if self.is_gold_earner:
            gold_earner_count = Character.objects.filter(
                user=self.user,
                is_gold_earner=True  # Changed from gold_earner to is_gold_earner
            ).count()
            if gold_earner_count > 6:
                raise ValueError(
                    "A party can have no more than 6 gold earners. Untick another character to make this one a gold earner.")

        super().save(*args, **kwargs)

    def user_can_access(self, user):
        """Check if the user can access this character"""
        return self.user == user


# ---------------------------- WEEKLY CONTENT ----------------------------

class WeeklyContent(models.Model):
    name = models.CharField(max_length=100, choices=RAID_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    min_ilvl = models.PositiveIntegerField()
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.difficulty})"


class Gate(models.Model):
    weekly_content = models.ForeignKey(WeeklyContent, related_name='gates', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    gold_amount = models.PositiveIntegerField()
    cooldown_weeks = models.PositiveIntegerField(default=0)  # 0 = available next week

    class Meta:
        unique_together = ('weekly_content', 'number')
        ordering = ['number']

    def __str__(self):
        return f"{self.weekly_content.name} - Gate {self.number}"


# ---------------------------- COMPLETION TRACKING ----------------------------

class CharacterWeeklyContent(models.Model):
    STATUS_CHOICES = [
        ('Not Done', 'Not Done'),
        ('Gate 2', 'Gate 2'),
        ('Gate 3', 'Gate 3'),
        ('Gate 4', 'Gate 4'),
        ('Completed', 'Completed'),
    ]

    character = models.ForeignKey(Character, related_name='weekly_contents', on_delete=models.CASCADE)
    weekly_content = models.ForeignKey(WeeklyContent, on_delete=models.CASCADE)
    week = models.DateField(default=get_current_week)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Done')
    completed_gates = models.ManyToManyField(Gate, through='CompletedGate', blank=True)

    class Meta:
        unique_together = ('character', 'weekly_content', 'week')

    def __str__(self):
        return f"{self.character.name} - {self.weekly_content.name} ({self.week})"

    def gold_earned(self):
        # Calculate total gold earned by summing up the gold amounts of completed gates
        return sum(entry.gate.gold_amount for entry in self.completed_gate_entries.all())

    def update_status(self):
        total_gates = self.weekly_content.gates.count()
        completed = self.completed_gate_entries.count()

        # Update the status based on the number of completed gates
        if completed == 0:
            self.status = 'Not Done'
        elif completed == 1 and total_gates > 1:
            self.status = 'Gate 2'
        elif completed == 2 and total_gates > 2:
            self.status = 'Gate 3'
        elif completed == 3 and total_gates > 3:
            self.status = 'Gate 4'
        elif completed == total_gates:
            self.status = 'Completed'
        self.save()

    def get_unlocked_gates(self):
        """
        Return gates that are available to complete for this character in this week.
        """
        gates = self.weekly_content.gates.all()
        locked_ids = set()

        previous_entries = CompletedGate.objects.filter(
            gate__in=gates,
            character_weekly_content__character=self.character
        ).exclude(character_weekly_content=self)

        for entry in previous_entries:
            cooldown = entry.gate.cooldown_weeks
            weeks_since = (self.week - entry.completed_at).days // 7
            if weeks_since <= cooldown:
                locked_ids.add(entry.gate.id)

        return gates.exclude(id__in=locked_ids)

    def get_status_display_choices(self):
        return self._meta.get_field('status').choices


class CompletedGate(models.Model):
    character_weekly_content = models.ForeignKey(CharacterWeeklyContent, on_delete=models.CASCADE,
                                                 related_name='completed_gate_entries')
    gate = models.ForeignKey(Gate, on_delete=models.CASCADE)
    completed_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('character_weekly_content', 'gate')

    def __str__(self):
        return f"{self.character_weekly_content} - Gate {self.gate.number} on {self.completed_at}"


# Signal to update the status and gold earned when a gate is completed

@receiver(post_save, sender=CompletedGate)
def update_character_weekly_content(sender, instance, **kwargs):
    # Get the CharacterWeeklyContent instance related to the CompletedGate
    character_weekly_content = instance.character_weekly_content

    # Update the gold earned for the weekly content
    character_weekly_content.update_status()

    # Recalculate and update the status and gold
    character_weekly_content.save()
