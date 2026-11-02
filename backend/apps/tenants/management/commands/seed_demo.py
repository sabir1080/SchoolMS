from django.core.management.base import BaseCommand

from apps.tenants.demo import DEMO_PASSWORD, SCHOOLS, seed_school, wipe_institutes


class Command(BaseCommand):
    help = (
        "Create (or rebuild) a demo institute: --school demo (Bright Future Academy, default) or "
        "--school scholars (Little Scholars School, Nursery to Class 3). Other institutes are not touched. "
        "With --wipe-all, first delete ALL institutes and their data."
    )

    def add_arguments(self, parser):
        parser.add_argument("--school", default="demo", help=f"Which demo school: {', '.join(SCHOOLS)} or all (comma separated).")
        parser.add_argument("--wipe-all", action="store_true", help="Delete every institute first (super admins and plans stay).")

    def handle(self, *args, school="demo", wipe_all=False, **options):
        codes = list(SCHOOLS) if school == "all" else [c.strip() for c in school.split(",") if c.strip()]
        unknown = [c for c in codes if c not in SCHOOLS]
        if unknown or not codes:
            self.stderr.write(f"Unknown demo school(s): {', '.join(unknown) or '-'}; choose from {', '.join(SCHOOLS)}.")
            raise SystemExit(1)
        if wipe_all:
            count, _ = wipe_institutes()
            self.stdout.write(f"Deleted {count} institute(s) and their data.")
        for code in codes:
            spec = SCHOOLS[code]
            tenant = seed_school(spec)
            logins = ["admin", *(t[0] for _c, _s, t, _n in spec["sections"] if t)][:3]
            logins += [spec["parent"][0], *(c["login"] for c in spec["children"] if c.get("login"))]
            self.stdout.write(self.style.SUCCESS(
                f"Demo institute '{tenant.name}' ready: code '{code}', users {'/'.join(logins)}..., password '{DEMO_PASSWORD}'."
            ))
