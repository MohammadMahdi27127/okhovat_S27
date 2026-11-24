import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.models import User, AuditEvent

class Command(BaseCommand):
    help = "Reset one verified member's password through a hidden prompt. Existing sessions become invalid."

    def add_arguments(self, parser):
        parser.add_argument("--code", required=True)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(pk=options["code"])
        except User.DoesNotExist:
            raise CommandError("Account not found.")
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Repeat password: "):
            raise CommandError("Passwords differ.")
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages))
        user.set_password(password)
        user.save(update_fields=["password"])
        AuditEvent.objects.create(action="operator_password_reset", target=user.pk)
        self.stdout.write(self.style.SUCCESS("Password updated."))
