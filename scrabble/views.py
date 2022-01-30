from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count
from django.shortcuts import redirect, render

from scrabble import profile_manager
from scrabble.forms import RegistrationForm
from scrabble.models import Room, UserProfile


def index(request):
    if request.user.is_authenticated:
        return redirect("/lobby")
    return redirect("/login")


def register_request(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("/")
        messages.error(request, "Unsuccessful registration. Invalid information.", extra_tags="danger")
    form = RegistrationForm()
    return render(request=request, template_name="register.html", context={"form": form})


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("/")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request=request, template_name="login.html", context={"form": form})


def logout_request(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have successfully logged out.")

    return redirect("/")


def lobby(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first.")
        return redirect("/login")

    rooms = Room.objects.all().filter(finished__exact=False)
    return render(request=request, template_name="lobby.html", context={"rooms": rooms})


def room(request, room_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first.")
        return redirect("/login")

    if Room.objects.get(id=room_id).join(request.user):
        return render(request=request, template_name="room.html", context={"room_id": room_id})
    else:
        return redirect("/lobby")


def create_room(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first.")
        return redirect("/login")

    room_name = request.GET.get("room_name")
    if room_name == "":
        room_name = "Room"

    new_room = Room.objects.create(name=room_name)
    return redirect("/room/" + str(new_room.id) + "/")


def profile(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first.")
        return redirect("/login")

    user_profile: UserProfile = profile_manager.get_profile_for(request.user)
    return render(request=request, template_name="profile.html", context={
        "username": request.user.username,
        "wins": user_profile.wins,
        "loses": user_profile.loses,
        "points": user_profile.totalScore
    })


def high_scores(request):
    top_points = UserProfile.objects.values('totalScore').order_by('-totalScore')[:10]
    top_wins = UserProfile.objects.values('wins').order_by('-wins')[:10]
    return render(request=request, template_name="high_scores.html", context={
        "top_points": top_points,
        "top_wins": top_wins
    })
