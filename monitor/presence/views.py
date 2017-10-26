import json

from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

def index(request):
    return HttpResponse("Hello, world.")

@csrf_exempt
def scanner(request):
    try:
        action = request.GET['action']
        room = request.GET['room']
    except:
        return HttpResponse(status=500, content='Not enough parameters')

    if request.body:
        data = json.loads(request.body.decode())
    else:
        data = None

    print(action, room, data)
    return HttpResponse("OK")
