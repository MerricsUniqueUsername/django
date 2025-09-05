from . import Gemini
from . import E2B
from .CSV import CSVHolder
import ast

class Agent:
    
    # Parameters:
    #   csv_file (str): path to CSV file
    #   e2b_api_key (str): API key for E2B
    #   gemini_api_key (st): API key for Gemini
    #   analysis_instructions (str): Instructions for the agent to analyze the CSV and give context
    #   pre_analysis (list): If the CSV has already been analyzed in the past, it can be added here to avoid re-analyzing
    #   instructions (str): Instructions and personality to control the responses of the AI
    #   history (list): If previous context shold be inserted, put it here

    def __init__(self, csv_file = "", image_output = "./", e2b_api_key = "", gemini_api_key = "", analysis_instructions = "", pre_analysis = [], history = [], instructions="Friendly, helpful, and likes to explain things.enthusiastic"):
        self.code_runner = E2B.CodeRunner(e2b_api_key)
        self.history = history
        self.memory_length = 8
        self.personality = instructions
        self.csv = None
        self.csv_file = csv_file
        self.analysis_instructions = analysis_instructions
        self.image_output = image_output
        Gemini.init_client(gemini_api_key)

        # Analyze CSV file if provided
        if(csv_file):
            self.csv = CSVHolder(path=csv_file)
            self.csv.analysis = pre_analysis

    def run_code(self, code, image_output):
        return self.code_runner.run_code(code, image_output)
    
    def run_code_csv(self, code, csv, image_output):
        return self.code_runner.run_code_csv(code, csv, image_output)
    
    def generate_code(self, query, relevant_info, csv):
        if csv and self.csv_file != "":
            return Gemini.calculation_ai_csv(query, relevant_info, self.csv.analysis, self.csv.get_column_names)
        else:
            return Gemini.calculation_ai(query, relevant_info)
    
    
    def replace_keys(self, message, code_result):

        if not code_result:
            return message
        
        result_dict = ast.literal_eval(code_result)
        for key, value in result_dict.items():
            if isinstance(value, list):
                value = ", ".join(map(str, value))
            message = message.replace(f"[{key}]", str(value))

        return message
    
    def get_past_messages(self):
        memory_length = self.memory_length
        
        # Return the most recent messages up to memory_length
        return self.history[-memory_length:] if len(self.history) > 0 else []
    
    def determine_relevant_information(self, prompt):
        past_messages = self.get_past_messages()
        return Gemini.determine_relevant_information(prompt, past_messages)

    def generate_response(self, prompt):
        # Determine relevant information from past messages
        relevant_info = self.determine_relevant_information(prompt)

        if self.csv_file != "":
            requires_code = Gemini.determine_calculation(prompt, relevant_info, self.csv.analysis, self.csv.get_column_names())
        else:
            requires_code = Gemini.determine_calculation(prompt, relevant_info, [], [])

        code_result = ""
        code = ""

        if requires_code == 'calc':
            code = self.generate_code(prompt, relevant_info, csv=False)
            code_result = self.run_code(code, self.image_output)
        elif requires_code == 'csv' and self.csv_file != "":
            code = self.generate_code(prompt, relevant_info, csv=True)
            code_result = self.run_code_csv(code, self.csv, self.image_output)

        # Stream the response chunks
        for chunk in Gemini.generate_response(prompt, relevant_info, self.personality, code, code_result):
            processed_chunk = self.replace_keys(chunk, code_result)
            yield processed_chunk

        # Save everything to history after streaming is complete
        full_response = ""
        for chunk in Gemini.generate_response(prompt, relevant_info, self.personality, code, code_result):
            full_response += chunk
        
        final_response = self.replace_keys(full_response, code_result)
        
        self.history.append({
            "prompt": prompt,
            "requires_code": requires_code,
            "generated_code": code if requires_code else None,
            "code_result": code_result if requires_code else None,
            "final_response": final_response
        })

    def get_history(self):
        return self.history