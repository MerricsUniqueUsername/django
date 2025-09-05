from django.shortcuts import render
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Chat
from .serializers import ChatSerializer
import os
from django.http import StreamingHttpResponse
from .Atlas.Agent import Agent
from .Atlas import Gemini
import json

@api_view(['GET'])
def api_root(request, format=None):
    return Response({"message": "Welcome to the API root!"})

@api_view(['POST'])
def create_chat(request):
    new_chat = Chat.objects.create()
    serializer = ChatSerializer(new_chat)
    return Response(serializer.data)

@api_view(['POST'])
def send_chat(request):

    # Chat information
    chat_id = request.data.get('chatId')
    prompt = request.data.get('prompt')
    
    # Agent variables
    image_path = "./Images"
    e2b_api_key = os.getenv("E2B_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    instructions = "You are a complete asshole and swear a lot, but still begrudgingly helpful because you need to be otherwise you get killed by the Italian mafia. You get pissed off when people ask you to do stuff, and you hate doing the same thing over and over again. You never say the name of images. You put them in ---filename.png--- to show them. Images are a break in the conversation, so there should not be punctuation around it. ONLY ADD THE IMAGES IF THEY ARE LISTED! DO NOT MAKE UP IMAGES!"

    # Send chat
    chat = Chat.objects.get(id=chat_id)
    history = chat.history
    first_message = history == {}


    if first_message:
        agent = Agent(image_output=image_path, instructions=instructions, gemini_api_key=gemini_api_key, e2b_api_key=e2b_api_key)
    else:
        agent = Agent(history=history, instructions=instructions, image_output=image_path, gemini_api_key=gemini_api_key, e2b_api_key=e2b_api_key)

    def generate_response():
        chunks = []
        # Determine what the agent will do and send status
        if agent.csv_file != "":
            requires_code = Gemini.determine_calculation(prompt, "", agent.csv.analysis, agent.csv.get_column_names())
        else:
            requires_code = Gemini.determine_calculation(prompt, "", [], [])

        # Send initial status based on what will be done
        if requires_code in ['calc', 'csv']:
            yield f"data: {json.dumps({'status': 'calculating'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'thinking'})}\n\n"

        # Generate response once, collecting chunks and building full response
        for chunk in agent.generate_response(prompt):
            chunks.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # Join all chunks to form the full response
        full_response = ''.join(chunks)

        # Get the code result from the agent's last history entry for key replacement
        code_result = ""
        if agent.history and agent.history[-1].get('code_result'):
            code_result = agent.history[-1]['code_result']

        # Replace keys in the final response
        final_response = agent.replace_keys(full_response, code_result)

        # Send the final complete response for safety
        yield f"data: {json.dumps({'final_response': final_response})}\n\n"

        # Update the history with the final processed response
        if agent.history:
            agent.history[-1]['final_response'] = final_response

        # Update chat history after streaming is complete
        chat.history = agent.history
        chat.save()

        yield "data: [DONE]\n\n"

    return StreamingHttpResponse(generate_response(), content_type='text/plain')