from dotenv import load_dotenv
load_dotenv()
from e2b_code_interpreter import Sandbox
from .CSV import CSVHolder
from PIL import Image
import io
import os
import boto3
from datetime import datetime
import pandas as pd

class CodeRunner:
    def __init__(self, api_key="", e2b_api_key=""):
        # Use e2b_api_key if provided, otherwise fall back to api_key
        self.api_key = e2b_api_key or api_key
        
        # AWS S3 Configuration
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
        )
    
    def upload_image_to_s3(self, image_data, file_name):
        """Upload image data to S3 and return the S3 URL"""
        try:
            s3_key = f"FitAI/Images/{file_name}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.BUCKET_NAME,
                Key=s3_key,
                Body=image_data,
                ContentType='image/png'
            )
            
            # Return the S3 URL
            s3_url = f"https://{self.BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return s3_url
            
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
            return None
    
    def run_code(self, code, image_output=None):
        # Create sandbox
        sbx = Sandbox()
        
        # Run code
        response = sbx.run_code(code)
        uploaded_urls = []
        
        try:
            result = response.logs.stdout[0]
            print(result)

            # Download pngs and upload to S3
            files = sbx.files.list("/home/user")
            for file in files:
                file_name = file.name
                
                # Check if the file is a PNG before attempting to read and upload
                if '.png' in file_name.lower():
                    
                    try:
                        # Try reading as binary first
                        content = sbx.files.read('/home/user/' + file_name, format='bytes')
                    except:
                        # Fallback: read normally and handle the content type
                        content = sbx.files.read('/home/user/' + file_name)
                        if isinstance(content, str):
                            # Convert string to bytes using latin-1 encoding to preserve byte values
                            content = content.encode('latin-1')
                    
                    # Verify it's a valid image and upload to S3
                    try:
                        image = Image.open(io.BytesIO(content))
                        # Convert back to bytes for S3 upload
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        # Upload to S3
                        s3_url = self.upload_image_to_s3(img_byte_arr.getvalue(), file_name)
                        if s3_url:
                            uploaded_urls.append(s3_url)
                            print(f"Image uploaded to S3: {s3_url}")
                    except Exception as e:
                        print(f"Error processing image {file_name}: {str(e)}")
                        
        except Exception as e:
            print("ERROR")
            result = "{'error': 'There was a calculation error while generating your message'}"

        # Clean up
        sbx.kill()
        
        # Return result and uploaded URLs
        return result
    
    def run_code_csv(self, code, csvholder: CSVHolder, image_output=None):
        sbx = Sandbox()
        uploaded_urls = []

        # Get dataframe from CSVHolder
        df = csvholder.df
        csv_content = df.to_csv(index=False)

        # Upload CSV to sandbox
        sbx.files.write("/data.csv", csv_content.encode('utf-8'))

        # Run code
        response = sbx.run_code(code)
        print(code)
        if len(response.logs.stdout) == 0:
            result = "{'error': 'There was a calculation error while generating your message'}"
            return result
        
        result = response.logs.stdout[0]
        
        # Download pngs and upload to S3
        files = sbx.files.list("/home/user")
        for file in files:
            file_name = file.name
            
            # Check if the file is a PNG before attempting to read and upload
            if '.png' in file_name.lower():
                
                try:
                    # Try reading as binary first
                    content = sbx.files.read('/home/user/' + file_name, format='bytes')
                except:
                    # Fallback: read normally and handle the content type
                    content = sbx.files.read('/home/user/' + file_name)
                    if isinstance(content, str):
                        # Convert string to bytes using latin-1 encoding to preserve byte values
                        content = content.encode('latin-1')
                
                # Verify it's a valid image and upload to S3
                try:
                    image = Image.open(io.BytesIO(content))
                    # Convert back to bytes for S3 upload
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    
                    # Upload to S3
                    s3_url = self.upload_image_to_s3(img_byte_arr.getvalue(), file_name)
                    if s3_url:
                        uploaded_urls.append(s3_url)
                        print(f"Image uploaded to S3: {s3_url}")
                except Exception as e:
                    print(f"Error processing image {file_name}: {str(e)}")

        # Clean up
        sbx.kill()
        
        return result