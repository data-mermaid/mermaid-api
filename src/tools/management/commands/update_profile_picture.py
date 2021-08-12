from time import sleep

from api.models import Profile
from api.utils.auth0utils import get_user_info
from .progress_bar_base_command import ProgressBarBaseCommand


class Command(ProgressBarBaseCommand):
    help = "Update profile picture from Auth0 profile"

    def add_arguments(self, parser):
        parser.add_argument(
            "--throttle",
            type=int,
            default=5,
            help="Number of auth0 profiles to fetch before 1 second break.",
        )

        parser.add_argument(
            "--profile_id",
            type=str,
            help="Only update profile for given profile id",
        )

    def update_profile_picture(self, profile):
        for auth_user in profile.authusers.all():
            user_info = get_user_info(auth_user.user_id)
            if not user_info["picture"]:
                continue
            profile.picture_url = user_info["picture"]
            profile.save()
            break

    def handle(self, *args, **options):
        throttle = options["throttle"]
        profile_id = options["profile_id"]

        qry = Profile.objects.all()
        if profile_id:
            qry = qry.filter(id=profile_id)

        num_profiles = qry.count()
        self.draw_progress_bar(0)
        n = 0
        for profile in qry:
            self.draw_progress_bar(float(n) / num_profiles)
            self.update_profile_picture(profile)
            if n == throttle - 1:
                print("break")
                sleep(1)
                n = 0
            n += 1

        self.draw_progress_bar(1)
