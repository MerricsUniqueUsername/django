from django.shortcuts import render
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

@api_view(['GET'])
def api_root(request, format=None):
    return Response({"message": "Welcome to the API root!"})