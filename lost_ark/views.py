from django.shortcuts import render


def home(request):
    return render(request, 'lost_ark/index.html')
