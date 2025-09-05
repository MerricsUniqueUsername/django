from django.shortcuts import render
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Chat
from .serializers import ChatSerializer

@api_view(['GET'])
def api_root(request, format=None):
    return Response({"message": "Welcome to the API root!"})

@api_view(['POST'])
def create_chat(request):
    new_chat = Chat.objects.create()
    serializer = ChatSerializer(new_chat)
    return Response(serializer.data)