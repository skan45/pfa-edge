import traci
import time
import boto3
import base64
#Send screenshot of the simulation to Kinesis Data Stream every 5 seconds
def send_image_to_kinesis(file_path):
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')

    kinesis = boto3.client('kinesis', region_name='us-east-1')
    kinesis.put_record(StreamName='TrafficDataStream', Data=encoded, PartitionKey='1')

traci.start(["sumo-gui", "-c", ""]) #Config file 
for step in range(1000):
    traci.simulationStep()
    if step % 50 == 0:  # every ~5 seconds
        file = "traffic_image.png"
        traci.gui.screenshot(viewID="View #0", filename=file)
        send_image_to_kinesis(file)
    time.sleep(0.1)

traci.close()
