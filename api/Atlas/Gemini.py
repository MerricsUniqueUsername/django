from google import genai
from google.genai.types import GenerateContentConfig
import google.generativeai as genai_stream
import ast

client = ""
calculation_ai_model = "gemini-2.0-flash"
explaination_ai_model = "gemini-2.5-flash-lite"
analysis_ai_model = "gemini-2.5-flash-lite"
final_message_model = "gemini-2.0-flash"

def init_client(api_key):
    global client
    client = genai.Client(api_key=api_key)
    genai_stream.configure(api_key=api_key)

#################################################################################
# Aanlyze a column of a CSV
#################################################################################
def analyze_column(column_data, analysis_instructions):
    response = client.models.generate_content(
        model=analysis_ai_model,
        contents=str(column_data),
        config=GenerateContentConfig(
            system_instruction=[
                "You are an AI that analyzes a column of a CSV file.",
                "You are given a sample of the column data as a list.",
                "You will return a summary of the column data and any insights you can find.",
                "Your goal is to provide a description of what type of answers are given and what the data looks like.",
                "Say what kind of data it is, is a number? long response? short response? categorical? multiple choice?",
                "Keep your response really short, no more than 3 sentences. Do not use markdown formatting",
                "If it seems like its multiple choice, write '[mc]' in your response.",
                "If it seems like a multiple choice, but they can select multiple responses, put [mult] after [mc]",
                "Things tend to be multiple choice if there are a lot of repeating answers",
                "Here are instructions given on what the data is like, if given at all, use this as context for the data and how to analyze it. This is most important while analyzing: " + analysis_instructions,
            ]
        ),
    )

    return response.text

#################################################################################
# Aanlyze multiple choice responses with multi-select
#################################################################################
def get_multiselect_choices(column_data):
    response = client.models.generate_content(
        model=analysis_ai_model,
        contents=str(column_data),
        config=GenerateContentConfig(
            system_instruction=[
                "You are given an array of checkbox responses with many responses",
                "Return an array of original responses",
                "Do not use markdown in your response",
                "Return the array, and nothing else",
                "Do not repeat the same category more than once",
                "Your goal is to look through the array given and make an array of original responses",
            ]
        ),
    )
    return response.text

def determine_relevant_columns(prompt, column_names, analysis):
    response = client.models.generate_content(
        model=explaination_ai_model,
        contents=str(prompt),
        config=GenerateContentConfig(
            system_instruction=[
                "You are an AI that determines what columns of a CSV file are relevant to the user's prompt.",
                "You are given a list of column names and a list of analysis of each column.",
                "You will return a list of column names that are relevant to the user's prompt.",
                "If no columns are relevant, return an empty list.",
                "Example response: ['column1', 'column2']",
                "Make sure you can answer all aspects of the prompt with the columns you choose, for example, if asking 'who' you would return names or anything of that sort",
                "Make sure to return all columns that can be relevant",
                "Here is the list of column names: " + str(column_names),
                "Here is the analysis of each column: " + str(analysis),
            ]
        ),
    )

    return response.text

#################################################################################
# Determine what information from past messages is relevant to the current prompt
#################################################################################
def determine_relevant_information(prompt, past_messages):
    # Format past messages with clear timestamps/ordering
    formatted_messages = []
    for i, msg in enumerate(past_messages, 1):
        formatted_messages.append(f"Message {i}: {msg}")
    
    response = client.models.generate_content(
        model=analysis_ai_model,
        contents=str(prompt),
        config=GenerateContentConfig(
            system_instruction=[
                "You are analyzing how a new user prompt relates to previous conversation messages.",
                "",
                "PAST MESSAGES (in chronological order, most recent last):",
                "\n".join(formatted_messages),
                "",
                "CURRENT PROMPT TO ANALYZE:",
                f"{prompt}",
                "",
                "INSTRUCTIONS:",
                "1. Pay special attention to temporal references in the current prompt like:",
                "   - 'the last message', 'your previous response', 'what you just said'",
                "   - 'earlier', 'before', 'previously mentioned'",
                "   - 'that', 'this', 'it' (referring to previous content)",
                "   - 'above', 'the data/numbers/info you gave'",
                "",
                "2. When the user refers to 'the last message' or similar, they typically mean the most recent message in the conversation.",
                "",
                "3. Look for contextual clues that connect the current prompt to specific past messages:",
                "   - Topic continuity (same subject matter)",
                "   - Direct references to data, numbers, or specific information shared earlier",
                "   - Follow-up questions or requests for clarification",
                "   - Pronouns or demonstratives pointing to previous content",
                "",
                "4. Provide a conversational summary that:",
                "   - Identifies which specific past message(s) are relevant",
                "   - Explains the connection between the current prompt and past messages",
                "   - Includes specific data, numbers, or details when referenced",
                "   - Clarifies what the user is building upon or responding to",
                "",
                "5. If no past messages are relevant to the current prompt, respond with: 'There is no relevant information from past messages.'",
                "",
                "Format your response in an explanational way. Explain to the next AI that will use your information how to use it to respond, like a plan",
                "NOTE: The person you are giving this plan to has NO IDEA what the previous messages were, so include information needed to acheive the plan",
                "Do this by adding a list of past message summaries that are relevant",
                "New messages do not have access to calculation variables that were returned earlier",
                "Make your response SUPER short, do not include a lot of information",
                "If anything in the past seems related or relevant, include it in your response",
            ]
        ),
    )
    relevant_info = response.text.strip()
    return relevant_info


#################################################################################
# Determine if the prompt requires code generation, csv analysis or not
#################################################################################
def determine_calculation(prompt, relevant_info, analysis, cols):
    response = client.models.generate_content(
        model=explaination_ai_model,
        contents=str(prompt),
        config=GenerateContentConfig(
            system_instruction=[
                "Assume a CSV was provided to you",
                "You are an AI that determines what type of processing a user prompt requires.",
                "You must return exactly one of these three options: 'csv', 'calc', or 'nocalc'",
                "The csv might contain a form, dataset, or any type of data",
                "",
                "Return 'csv' if:",
                "- The prompt asks about data in a CSV file",
                "- The prompt requires counting, analyzing, or processing CSV data",
                "- The prompt mentions rows, columns, entries, or other CSV-related operations",
                "- The information might be contained in the CSV information",
                "- If asking about any columns of the CSV, which is: " + str(cols),
                "- The analysis shows CSV data is available: " + str(analysis),
                "- If the analysis is empty or does not exist, never return 'csv'",
                "- Asking for graphs based on CSV data",
                "",
                "Return 'calc' if:",
                "- The prompt requires mathematical calculations NOT related to CSV data",
                "- The prompt involves data analysis that isn't CSV-based",
                "- Asking for graphs",
                "- If computer power needs to be used to answer question."
                "",
                "Return 'nocalc' if:",
                "- The prompt is a simple question that doesn't require calculations or data processing",
                "- The answer can be provided from existing information without computation",
                "- No mathematical operations or data analysis is needed",
                "- If asking to just show expressions",
                "",
                "Example: if asking 'show me a formula for variance' use nocalc if they are just asking for a formula.",
                "Important: Questions like 'how many X are there?' typically require counting, which means:",
                "- If X refers to CSV data → return 'csv'",
                "- If X refers to other countable items → return 'calc'",
                "",
                "Context from previous messages (use this to avoid redundant calculations):",
                relevant_info,
                "",
                "Analyze the prompt carefully and return only the single word response.",
            ]
        ),
    )

    result = response.text.strip().lower()
    return result

#################################################################################
# AI for calculations
#################################################################################
def calculation_ai(query, relevant_info):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=str(query),
        config=GenerateContentConfig(
            system_instruction = [
                "You are an AI that calculates what needs to be calculated for the prompt.",
                "You are not talking to the user, you are just calculating.",
                "You write all your code in Python",
                "The prompt could be asking for many things, so you will need to calculate multiple things if needed.",
            
                "IMPORTANT: You MUST return results in a completely flat dictionary format with NO nesting whatsoever.",
                "Every key in your result dictionary must map directly to a simple value (string, number, boolean).",
                "NEVER create dictionaries inside dictionaries, lists of dictionaries, or any nested structures.",
                
                "WRONG examples (DO NOT DO THIS):",
                "❌ {'results': {'result1': 1, 'result2': 2}}  # Dictionary inside dictionary",
                "❌ {'stats': [{'mean': 5}, {'max': 10}]}      # List of dictionaries", 
                "❌ {'data': {'sales': {'q1': 100}}}           # Multiple levels of nesting",
                
                "CORRECT examples (DO THIS):",
                "✅ {'result1': 1, 'result2': 2, 'result3': 3}",
                "✅ {'mean_value': 5, 'max_value': 10, 'count': 100}",
                "✅ {'q1_sales': 100, 'q2_sales': 150, 'total_sales': 250}",
                
                "If you have multiple related calculations, create separate top-level keys instead of grouping them.",
                "For example, instead of {'workout': {'sets': 3, 'reps': 10}}, use {'workout_sets': 3, 'workout_reps': 10}",
                
                "For each result you return, it should not look like code. It should look like a string that is neatly formatted. For example, an array should not be {'result': [1,2,3]} but instead {'result': '1, 2, 3'} if thats the best way to format it",
                "Put in extra work to make sure the dict is formatted nicely.",
                "Do not put sentences or anything in these dicts. This is strictly for calculation, do not conversate at all.",
                "Print out the final dict result only, nothing else.",
                "Use markdown for formatting the strings inside the dict.",
                "Do not try to add to the conversation with your code. You are just calculating, so do not generate long strings",
                "Give each graph a random UUID name, import uuid",
                "Include the name of each graph in the printed dict",
                'To save a plot: plt.savefig("name.png", format="png")\t plt.close()',
                "Never address previous messages by number",
                "Put any assumptions you make in the dict as well, for example if you assume the user wants to calculate the sum of a list of numbers, put that in the dict as well.",
                "You should not be doing anything intensive, such as web scraping or database queries, making UIs, or anything that requires a lot of resources.",
                "Do not write unsafe, overcalculation code or anything unsafe. Keep it simple, the code should finish running quickly",
            ]
        ),
    )

    analyzed_text = response.text.replace("```python", "").replace("```", "").strip()
    return analyzed_text


#################################################################################
# AI for calculations
#################################################################################
def calculation_ai_csv(query, relevant_info, csv_analysis, csv_columns):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=str(query),
        config=GenerateContentConfig(
            system_instruction = [
                "You are an AI that calculates what needs to be calculated for the prompt.",
                "You are not talking to the user, you are just calculating.",
                "You write all your code in Python",
                "The prompt could be asking for many things, so you will need to calculate multiple things if needed.",
                
                "IMPORTANT: You MUST return results in a completely flat dictionary format with NO nesting whatsoever.",
                "Every key in your result dictionary must map directly to a simple value (string, number, boolean).",
                "NEVER create dictionaries inside dictionaries, lists of dictionaries, or any nested structures.",
                
                "WRONG examples (DO NOT DO THIS):",
                "❌ {'results': {'result1': 1, 'result2': 2}}  # Dictionary inside dictionary",
                "❌ {'stats': [{'mean': 5}, {'max': 10}]}      # List of dictionaries", 
                "❌ {'data': {'sales': {'q1': 100}}}           # Multiple levels of nesting",

                "CORRECT examples (DO THIS):",
                "✅ {'result1': 1, 'result2': 2, 'result3': 3}",
                "✅ {'mean_value': 5, 'max_value': 10, 'count': 100}",
                "✅ {'q1_sales': 100, 'q2_sales': 150, 'total_sales': 250}",
                
                "If you have multiple related calculations, create separate top-level keys instead of grouping them.",
                "For example, instead of {'workout': {'sets': 3, 'reps': 10}}, use {'workout_sets': 3, 'workout_reps': 10}",
                
                "For each result you return, it should not look like code. It should look like a string that is neatly formatted. For example, an array should not be {'result': [1,2,3]} but instead {'result': '1, 2, 3'} if thats the best way to format it",
                "Put in extra work to make sure the dict is formatted nicely.",
                "Do not put sentences or anything in these dicts. This is strictly for calculation, do not conversate at all.",
                "Print out the final dict result only, nothing else.",
                "Use markdown for formatting the strings inside the dict.",
                "Do not try to add to the conversation with your code. You are just calculating, so do not generate long strings",
                "Give each graph a random UUID name, import uuid",
                "Include the name of each graph in the printed dict",
                'To save a plot: plt.savefig("name.png", format="png")\t plt.close()',
                "There is a file path called '/data.csv' that you can use to analyze data",
                "Here is the analysis of each column in the DataFrame. Make sure each calculation is done in accordance to the analysis, and each column that is being analyzed is also makes sense: " + str(csv_analysis),
                "Here is the list of column names in the DataFrame: " + str(csv_columns),
                "Never address previous messages by number",
                "Put any assumptions you make in the dict as well, for example if you assume the user wants to calculate the sum of a list of numbers, put that in the dict as well.",
                "You should not be doing anything intensive, such as web scraping or database queries, making UIs, or anything that requires a lot of resources.",
                "Do not write unsafe, overcalculation code or anything unsafe. Keep it simple, the code should finish running quickly",
            ]
        ),
    )

    analyzed_text = response.text.replace("```python", "").replace("```", "").strip()
    return analyzed_text

#################################################################################
# AI for response generation
#################################################################################
def generate_response(prompt, relevant_info, personality, code, code_result=None):
    if code_result:
        prompt += f"\n\nHere is the result of the code execution. You can only put the [variables] in your response if it contains one of these keys:\n{code_result}"

    # Get keys
    keys = []
    if code_result:
        try:
            result_dict = ast.literal_eval(code_result)
            keys = list(result_dict.keys())
        except Exception as e:
            print(f"Error parsing code result: {str(e)}")
    
    # Get list of keys for the system instruction
    keys_list = ", ".join([f"[{key}]" for key in keys])
    print(keys_list)
        
    # Construct the list of system instructions
    system_instructions_list = [
        "This is your extra instructions, of most importance: " + personality,
        "Act as if you are an actual person with this personality.",
        "You are an assistant that generates a response to the user's prompt.",
        "Do not act as a robot, and say stuff like, 'im trained that way.'",
        "If asked how you know something or an explanation, do not say 'I am trained that way' or 'I am an AI'. If asked why or to explain, give them analogies or examples or proofs. Do not do such a thing unless asked, however.",
        "You will use the result of the code execution if provided, if it exists. If it does not exist, do not mention anything about it",
        "Make sure to format your response nicely and clearly.",
        "Use Mathjax to give math expressions",
        "Here is a list of all the keys you can use in your response. Do not add any more for any reason: " + keys_list,
    ]

    # Add specific instructions related to code execution results if they are provided
    if code_result:
        system_instructions_list.extend([
            "For each key in the code execution result, to insert it into the response, simply put [key] in the response where you want the value to be inserted.",
            "The keys should be named exactly as they are in the code execution result, case sensitive and all.",
            "For example, if the code execution result is {'result': '1, 2 , 3'}, you can use [result] in your response to insert '1, 2, 3'.",
            "DO NOT include any [result names] that are not in the code execution for any reason.",
            "If an execution result does not have a variable name, do not make one up. DO NOT FOR FUCKS SAKE MAKE ONE UP! ONLY PUT A VARIABLE NAME IN THERE IF IT FUCKING EXISTS!",
            "Inside the braces for adding your variables to the response, make sure the name is character for character exactly with one of the variables. Do not include extra characters in there such as '\\'.",
            "Only insert images generated in the code result into the message. Do this by putting '---image_name.png---' in the message.",
            "To show an image, it must be in ---image_name.png--- to be actually seen, otherwise it will not be visible",
            "Never ever just type out the code execution result in your response, always format it nicely.",
            "Do not mention code execution result in your response, just use it to generate the response.",
            "DO NOT FUCKING MAKE VARIABLE NAMES UP! REFER TO: " + code_result,
        ])

    # Add final general instructions
    system_instructions_list.extend([
        "Use markdown for formatting your response",
        "When referring to past messages, do not say 'message 1' or anything like that.",
        "Here is the code (if any) that was generated for the prompt. Use this to help explain how you got your answer, but do not talk as if you're talking about code: " + code,
        "You will use the relevant information from past messages to help you generate the response.",
        "Here is the relevant info. Use it to respond conversational way: " + relevant_info,
        "You cannot generate images, unless it is a graph",
    ])

    # Join the list of system instructions into a single string.
    # The `system_instruction` argument in the `GenerativeModel` constructor expects a string.
    final_system_instruction = "\n".join(system_instructions_list)

    # Initialize the GenerativeModel INSIDE the function for each call
    # This allows you to pass a dynamic `system_instruction` argument.
    model = genai_stream.GenerativeModel(
        final_message_model, # Use the model name from your original code
        system_instruction=final_system_instruction # Pass the combined instructions here
    )

    # Generate content using the initialized model, enabling streaming.
    # The system_instruction is now part of the model's configuration.
    response_generator = model.generate_content(
        contents=prompt,
        stream=True,
    )

    # Yield each chunk as it arrives for streaming
    for chunk in response_generator:
        if chunk.text:
            yield chunk.text
