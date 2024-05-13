from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.db.models.signals import pre_delete
from django.dispatch import receiver

class CasovyModel(models.Model):
    vytvoreny = models.DateTimeField(default=timezone.now, editable=False)
    aktualizovany = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

class Atribut(CasovyModel):
    nazov = models.CharField(max_length=255)
    typ = models.CharField(max_length=100)

    def __str__(self):
        return self.nazov

class Formular(CasovyModel):
    formular_nazov = models.CharField(max_length=255)
    # A new field to indicate if the form should be included in a gallery
    zobrazit_v_galerii = models.BooleanField(default=False)

    def __str__(self):
        return self.formular_nazov

class Zaznam(CasovyModel):
    # Linking each record to a User
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    opis = models.TextField(default="")
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE, null=True)  # Link Record to Form
    
    def upvote(self, user):
        Zaznam.objects.create(record=self, user=user, vote_type='up')

    def downvote(self, user):
        Zaznam.objects.create(record=self, user=user, vote_type='down')
    
    def net_votes(self):
        return self.thumb_up - self.thumb_down
        
    def get_comments(self):
        return Zaznam_Komentar.objects.filter(record=self).order_by('-created_at')

    def __str__(self):
        return f'Record {self.id}'
    
    # Define a signal handler for pre-delete of Form
@receiver(pre_delete, sender=Formular)
def delete_records_with_form(sender, instance, **kwargs):
    records_to_delete = Zaznam.objects.filter(formular=instance)
    records_to_delete.delete()
    
class Hlas(CasovyModel):
    VOTE_TYPE_CHOICES = (
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    zaznam = models.ForeignKey(Zaznam, on_delete=models.CASCADE)
    typ_hlasu = models.CharField(max_length=10, choices=VOTE_TYPE_CHOICES)

    class Meta:
        unique_together = ('user', 'zaznam')  # Prevents multiple votes on the same record by the same user


class Zaznam_Komentar(CasovyModel):
    zaznam = models.ForeignKey(Zaznam, on_delete=models.CASCADE, null=True)
    komentar = models.TextField(default="")
    # Linking each comment to a User
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    povoleny_adminom = models.BooleanField(default=True)

    def __str__(self):
        return f'Comment by {self.user.username} on Record {self.zaznam.id}'



class Formular_Atribut(CasovyModel):
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE)
    atribut = models.ForeignKey(Atribut, on_delete=models.CASCADE)
    povinny = models.BooleanField(default=True)
    # A new field to indicate if the attribute should be displayed in the gallery
    zobrazit_v_galerii = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.atribut.name} in {self.formular.formular_nazov}'

class Formular_Atribut_Udaje(CasovyModel):
    zaznam = models.ForeignKey(Zaznam, on_delete=models.CASCADE, null=True)
    formular_atribut = models.ForeignKey(Formular_Atribut, on_delete=models.CASCADE)
    hodnota = models.CharField(max_length=512, blank=True, null=True)
    
    def __str__(self):
        return self.hodnota


# Gallery table is replaced by a flag in FormAttribute to indicate if an attribute should be shown in the gallery

# A model to manage gallery settings for a form without creating additional tables
class Galeria(CasovyModel):
    galeria_nazov = models.CharField(max_length=255, default="")
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE, related_name="galleries")

    def __str__(self):
        return f'Gallery for {self.formular.formular_nazov}'

    class Meta:
        unique_together = ('formular', 'vytvoreny')  # Ensures each gallery is unique for a form at a given creation time


