import pandas as pd
from . import Gemini
from pathlib import Path
import ast
import boto3
import io

class CSVHolder:
    def __init__(self, path: str):

        # AWS S3 Configuration
        BUCKET_NAME = "atlas07072025"
        AWS_ACCESS_KEY_ID = "AKIARIHPM7YSWMRX2YSF"
        AWS_SECRET_ACCESS_KEY = "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"

        # Get file from S3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        # Download the file from S3
        s3_key = f"FitAI/WorkoutData/{Path(path).name}"
        response = self.s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        csv_content = response['Body'].read().decode('utf-8')
        self.df = pd.read_csv(io.StringIO(csv_content))
        self.path = path

        # Analysis of columns
        self.analysis = []

    def get_as_string(self):
        return self.df.to_csv(index=False)

    def analyze(self, analysis_instructions):

        print("Analyzing CSV file...")

        # Reset analysis
        self.analysis = []

        # Get basic info
        row_count = self.get_row_count()
        column_names = self.get_column_names()

        # Sample data for analysis
        sample_number = min(15, row_count)
        sample_data = self.get_sample(sample_number)
        sample_column_data = []
        for name in column_names:
            sample_column_data.append({name : []})
            self.analysis.append({name : ""})
        for data in sample_data:
            for name in column_names:
                sample_column_data[column_names.index(name)][name].append(data[name])

        # Analyze all the sampled data
        for column_data in sample_column_data:
            for column_name, data in column_data.items():
                analysis = Gemini.analyze_column(data, analysis_instructions)
                if "[mc]" in analysis and "[mult]" not in analysis:

                    # Record each original appearance
                    original_responses = self.df[column_name].drop_duplicates().tolist()
                    analysis += " Here are the original responses for this: " + str(original_responses)
                
                if "[mult]" in analysis:
                    original_responses = self.df[column_name].drop_duplicates().tolist()
                    original_responses = ast.literal_eval(Gemini.get_multiselect_choices(original_responses))
                    analysis += " Here are the original responses for this: " + str(original_responses)

                self.analysis[column_names.index(column_name)][column_name] = analysis

        print("Analysis complete.")

    def get_relevant_data(self, prompt: str):
        """Returns the relevant data from the CSV file based on the prompt."""
        relevant_columns = self.determine_relevant_columns(prompt)
        return self.get_colmns_data(relevant_columns)

    def determine_relevant_columns(self, prompt: str):

        if self.analysis == []:
            raise ValueError("You must run analyze() before determining relevant columns.")
        
        column_names = self.get_column_names()
        relevant_columns = Gemini.determine_relevant_columns(prompt, column_names, self.analysis)
        return ast.literal_eval(relevant_columns)

    def get_column_names(self):
        """Returns the names of the columns in the CSV file."""
        return self.df.columns.tolist()
    
    def get_row_count(self):
        """Returns the number of rows in the CSV file."""
        return len(self.df)
    
    def get_column_data(self, column_name: str):
        """Returns the data of a specific column in the CSV file."""
        if column_name not in self.df.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the CSV file.")
        return self.df[column_name].tolist()
    
    def get_row_data(self, row_index: int):
        """Returns the data of a specific row in the CSV file."""
        if row_index < 0 or row_index >= len(self.df):
            raise IndexError(f"Row index {row_index} is out of bounds.")
        return self.df.iloc[row_index].to_dict()
    
    def get_colmns_data(self, column_names: list):
        """Returns the data of specific columns in the CSV file."""
        if not all(col in self.df.columns for col in column_names):
            raise ValueError(f"One or more columns {column_names} do not exist in the CSV file.")
        return self.df[column_names].to_dict(orient='list')

    def get_sample(self, size):
        """Returns a random row from the CSV file."""
        if size < 1 or size > len(self.df):
            raise ValueError(f"num_rows must be between 1 and {len(self.df)}.")
        return self.df.sample(n=size).to_dict(orient='records')