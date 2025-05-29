import boto3
import base64
import time
import os


stream_name = 'TrafficDataStream'
region_name = 'eu-west-1'  
screenshots_dir = ''  # Where SUMO saves screenshots
interval = 10  # in seconds

# Initialize Kinesis client
kinesis_client = boto3.client('kinesis', region_name=region_name)

def send_screenshot_to_kinesis(image_path):
    with open(image_path, 'rb') as image_file:
        image_bytes = image_file.read()
        # You can base64 encode if needed
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=encoded_image,
            PartitionKey="partition-key"
        )
        print(f"Sent {image_path} to Kinesis. Response: {response}")

def watch_and_send():
    sent_files = set()

    while True:
        for filename in os.listdir(screenshots_dir):
            if filename.endswith('.png') or filename.endswith('.jpg'):
                file_path = os.path.join(screenshots_dir, filename)
                if file_path not in sent_files:
                    send_screenshot_to_kinesis(file_path)
                    sent_files.add(file_path)
        time.sleep(interval)

if __name__ == '__main__':
    watch_and_send()
