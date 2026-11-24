import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.models import User

class Command(BaseCommand):
    help = "Create an explicitly requested account, prompting for a password."

    def add_arguments(self, parser):
        parser.add_argument("--code", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--ring", default="")
        parser.add_argument("--team", default="")
        for flag in ("admin", "coach", "ring-leader", "workgroup-manager"):
            parser.add_argument("--" + flag, action="store_true")

    def handle(self, *args, **options):
        if User.objects.filter(pk=options["code"]).exists():
            raise CommandError("This group code already exists.")
        user = User(code=options["code"], name=options["name"], ring=options["ring"], team=options["team"],
                    is_admin=options["admin"], is_coach=options["coach"],
                    is_ring_leader=options["ring_leader"], is_workgroup_manager=options["workgroup_manager"])
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            raise CommandError("Passwords differ.")
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as error:
            raise CommandError("; ".join(error.messages))
        user.save()
        self.stdout.write(self.style.SUCCESS("Account created."))
