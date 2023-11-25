from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

class Attribute(TimeStampedModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Form(TimeStampedModel):
    form_name = models.CharField(max_length=255)
    # A new field to indicate if the form should be included in a gallery
    included_in_gallery = models.BooleanField(default=False)

    def __str__(self):
        return self.form_name

class Record(TimeStampedModel):
    # Linking each record to a User
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    description = models.TextField(default="")
    
    def upvote(self, user):
        Vote.objects.create(record=self, user=user, vote_type='up')

    def downvote(self, user):
        Vote.objects.create(record=self, user=user, vote_type='down')
    
    def net_votes(self):
        return self.thumb_up - self.thumb_down
        
    def get_comments(self):
        return RecordComment.objects.filter(record=self).order_by('-created_at')

    def __str__(self):
        return f'Record {self.id}'
    
class Vote(TimeStampedModel):
    VOTE_TYPE_CHOICES = (
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_TYPE_CHOICES)

    class Meta:
        unique_together = ('user', 'record')  # Prevents multiple votes on the same record by the same user


class RecordComment(TimeStampedModel):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, null=True)
    comment = models.TextField(default="")
    # Linking each comment to a User
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    aproved_by_admin = models.BooleanField(default=True)

    def __str__(self):
        return f'Comment by {self.user.username} on Record {self.record.id}'



class FormAttribute(TimeStampedModel):
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    # A new field to indicate if the attribute should be displayed in the gallery
    display_in_gallery = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.attribute.name} in {self.form.form_name}'

class FormAttributeData(TimeStampedModel):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, null=True)
    form_attribute = models.ForeignKey(FormAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.value


# Gallery table is replaced by a flag in FormAttribute to indicate if an attribute should be shown in the gallery

# A model to manage gallery settings for a form without creating additional tables
class Gallery(TimeStampedModel):
    gallery_name = models.CharField(max_length=255, default="")
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="galleries")

    def __str__(self):
        return f'Gallery for {self.form.form_name}'

    class Meta:
        unique_together = ('form', 'created_at')  # Ensures each gallery is unique for a form at a given creation time


