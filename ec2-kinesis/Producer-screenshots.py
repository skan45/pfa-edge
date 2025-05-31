import traci
import os
import time
import boto3

# Configuration
SUMO_CMD = ["sumo-gui", "-c", "sumo_config.sumocfg", "--start"]
OUTPUT_DIR = "red_light_captures"
VIEW_ID = "View #0"
SIMULATION_DURATION = 3600  # 1 hour of simulation (3600 steps)
SIMULATION_SPEED = 5.0  # 1.0 = real time
stream_name = 'TrafficDataStream'
region_name = 'eu-west-1'  

def initialize_simulation():
    """Initialize SUMO and create output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    traci.start(SUMO_CMD)
    time.sleep(2)  # Allow GUI to load
    traci.gui.setSchema(VIEW_ID, "real world")  # Use real-world visualization
    print("Simulation started and initialized.")

def capture_full_simulation_view(step):
    """Set the view to show the full simulation and take a screenshot."""
    try:
        # Get simulation boundary (xmin, ymin, xmax, ymax)
        boundary = traci.simulation.getNetBoundary()
        xmin, ymin = boundary[0]
        xmax, ymax = boundary[1]

        # Set GUI view and take screenshot
        traci.gui.setBoundary(VIEW_ID, xmin, ymin, xmax, ymax)
        traci.gui.setZoom(VIEW_ID, 100)  # Optional: Adjust zoom level

        filename = os.path.join(OUTPUT_DIR, f"red_light_step_{step:04d}.png")
        traci.gui.screenshot(VIEW_ID, filename)
        print(f"[{step}] Red light detected — Screenshot saved: {filename}")
        # Send to AWS Kinesis
        with open(filename, "rb") as img_file:
            image_bytes = img_file.read()
            response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=image_bytes,
            PartitionKey="partition-key"
        )
        print(f"Sent {image_path} to Kinesis. Response: {response}")

    except Exception as e:
        print(f"[{step}] Failed to capture view: {e}")

def main():
    # Initialize Kinesis client
    kinesis_client = boto3.client('kinesis', region_name=region_name)
    initialize_simulation()

    try:
        for step in range(SIMULATION_DURATION):
            traci.simulationStep()

            # Capture only every 5 steps
            if step % 5 == 0:
                # Check for red light in any traffic light
                tls_ids = traci.trafficlight.getIDList()
                red_light_detected = any(
                    'r' in traci.trafficlight.getRedYellowGreenState(tls_id) or
                    'R' in traci.trafficlight.getRedYellowGreenState(tls_id)
                    for tls_id in tls_ids
                )

                if red_light_detected:
                    capture_full_simulation_view(step)

            time.sleep(1.0 / SIMULATION_SPEED)

    except Exception as e:
        print(f"Simulation error: {e}")
    finally:
        traci.close()
        print("Simulation ended.")

if __name__ == "__main__":
    main()
