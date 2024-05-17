from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.db.models.signals import pre_delete
from django.dispatch import receiver


"""

Súbor models.py je ďalšou kľúčovou súčasťou Django aplikácie. Slúži na definovanie modelov, ktoré predstavujú štruktúru vašich dát. 
Tieto modely sa následne premapujú na databázové tabuľky.
Ako fungujú modely v Django?

    Definícia modelu: V súbore models.py definujete triedy, ktoré zdedia z triedy models.Model od Django. 
                      Každý atribút v tejto triede zodpovedá jednému stĺpcu v databázovej tabuľke.
    Typy dát: Pri definícii atribútu určujete aj jeho typ dát pomocou rôznych polí z modulu models. 
                Napríklad, models.CharField pre textové reťazce, models.IntegerField pre celé čísla, alebo 
                models.DateTimeField pre dátum a čas.
    Metadáta modelu: Môžete tiež definovať triedu Meta vnútri modelu a pomocou nej určiť rôzne metadáta, 
                     ako napríklad názov tabuľky v databáze alebo či je model abstraktný (nepremapuje sa na samostatnú tabuľku).

"""

# Základná trieda pre reprezentáciu časových atribútov
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
    # Nové pole na označenie, či je formulár zobrazený v nejakej galérií
    zobrazit_v_galerii = models.BooleanField(default=False)

    def __str__(self):
        return self.formular_nazov

class Zaznam(CasovyModel):
    # Prepojenie každého záznamu s používateľom
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    opis = models.TextField(default="")
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE, null=True)
    
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
    
# Definujte obsluhu signálu na predbežné vymazanie formulára
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
        unique_together = ('user', 'zaznam')  # Zabráni viacnásobnému hlasovaniu v rovnakom zázname tým istým používateľom


class Zaznam_Komentar(CasovyModel):
    zaznam = models.ForeignKey(Zaznam, on_delete=models.CASCADE, null=True)
    komentar = models.TextField(default="")
    # Prepojenie každého komentára s používateľom
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    povoleny_adminom = models.BooleanField(default=True)

    def __str__(self):
        return f'Comment by {self.user.username} on Record {self.zaznam.id}'



class Formular_Atribut(CasovyModel):
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE)
    atribut = models.ForeignKey(Atribut, on_delete=models.CASCADE)
    povinny = models.BooleanField(default=True)
    # Nové pole na označenie, či sa má atribút zobraziť v galérii
    zobrazit_v_galerii = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.atribut.nazov} in {self.formular.formular_nazov}'

class Formular_Atribut_Udaje(CasovyModel):
    zaznam = models.ForeignKey(Zaznam, on_delete=models.CASCADE, null=True)
    formular_atribut = models.ForeignKey(Formular_Atribut, on_delete=models.CASCADE)
    hodnota = models.CharField(max_length=512, blank=True, null=True)
    
    def __str__(self):
        return self.hodnota


class Galeria(CasovyModel):
    galeria_nazov = models.CharField(max_length=255, default="")
    formular = models.ForeignKey(Formular, on_delete=models.CASCADE, related_name="galleries")

    def __str__(self):
        return f'Gallery for {self.formular.formular_nazov}'

    class Meta:
        unique_together = ('formular', 'vytvoreny')  # Zabezpečuje, že každá galéria je jedinečná pre formulár v danom čase vytvorenia


