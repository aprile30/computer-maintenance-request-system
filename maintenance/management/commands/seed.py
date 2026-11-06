from django.core.management.base import BaseCommand

from maintenance.models import Computer, IssueCategory, Location, User


class Command(BaseCommand):
    help = "Creates demo accounts and sample records for testing."

    def handle(self, *args, **options):
        def make(username, password, role, first, last, dept=""):
            u, created = User.objects.get_or_create(username=username, defaults={
                "role": role, "first_name": first, "last_name": last, "department": dept,
                "email": f"{username}@example.com"})
            if created:
                u.set_password(password)
                if role == "admin":
                    u.is_staff = True
                u.save()
            return u

        make("admin", "admin12345", "admin", "System", "Administrator", "ICT Office")
        make("tech1", "tech12345", "technician", "Juan", "Technician", "ICT Office")
        make("faculty1", "faculty12345", "requester", "Maria", "Faculty", "BSIT")

        for name in ["Hardware", "Software", "Network", "Peripherals"]:
            IssueCategory.objects.get_or_create(name=name)

        lab, _ = Location.objects.get_or_create(name="Computer Lab 1", defaults={"building": "IT Building"})
        for i in range(1, 4):
            Computer.objects.get_or_create(property_no=f"LAB1-PC-0{i}", defaults={
                "location": lab, "brand": "Generic", "model": "Desktop"})

        self.stdout.write(self.style.SUCCESS(
            "Done. Logins: admin / admin12345, tech1 / tech12345, faculty1 / faculty12345"))
