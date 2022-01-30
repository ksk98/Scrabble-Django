from django.contrib.auth.models import User

from scrabble.models import UserProfile


def get_profile_for(user: User) -> UserProfile:
    if not UserProfile.objects.filter(user=user).exists():
        UserProfile(user=user).save()

    return UserProfile.objects.get(user=user)
