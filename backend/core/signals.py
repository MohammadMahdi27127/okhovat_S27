from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Revision, identifier

@receiver(post_save)
@receiver(post_delete)
def invalidate_state(sender, **kwargs):
    if sender._meta.app_label == "core" and sender not in (Revision,):
        Revision.objects.update_or_create(pk=1, defaults={"rev": identifier()})
