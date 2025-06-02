import base64
import boto3
import cv2
import logging
import numpy as np
import re
import math
from datetime import datetime

# Setup logger for AWS CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('NumberCarsPerImg')  # Update if needed

# --- Decode base64 images from Kinesis ---
def pull_from_kinesis(event):
    logger.info("📥 Pulling images from Kinesis event.")
    images = []

    for idx, record in enumerate(event['Records']):
        try:
            raw_data = record['kinesis']['data']
            clean_data = re.sub(r'\s+', '', raw_data)
            if len(clean_data) % 4 != 0:
                clean_data += '=' * (4 - len(clean_data) % 4)
            image_bytes = base64.b64decode(clean_data)
            images.append(image_bytes)
            logger.info("✅ Decoded image")
        except Exception as e:
            logger.error(f"❌ Failed to decode record {idx+1}: {e}", exc_info=True)

    return images

# --- Define lanes using fixed pixel sizes relative to image dimensions ---
def get_absolute_rect(x1, y1, w, h):
    return (x1, y1, x1 + w, y1 + h)

# --- Count blue cars per lane ---
def count_blue_cars_per_lane(image_bytes):
    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        logger.error("❌ Failed to decode image.")
        return None

    height, width, _ = image.shape

    lanes = {
        "top":    get_absolute_rect(0, 0, 294, 56),                   
        "left":   get_absolute_rect(0, height - 78, 280, 78),         
        "bottom": get_absolute_rect(width - 296, height - 65, 296, 65),
        "right":  get_absolute_rect(width - 280, 0, 280, 78),         
    }

    raw_counts = {lane: 0 for lane in lanes}

    # Convert image to HSV and apply blue color filter
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([90, 100, 20])
    upper_blue = np.array([140, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Reduce noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find blue contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 50 < area < 5000:
            x, y, w, h = cv2.boundingRect(cnt)
            cx, cy = x + w // 2, y + h // 2

            for lane, (x1, y1, x2, y2) in lanes.items():
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    raw_counts[lane] += 1
                    break

    return raw_counts

# --- Store result in DynamoDB ---
def store_result_in_dynamodb(adjusted_counts):
    timestamp = datetime.utcnow().isoformat()
    pk_value = f"road_capture_{timestamp}"

    west_east = adjusted_counts.get("left", 0) + adjusted_counts.get("right", 0)
    north_south = adjusted_counts.get("top", 0) + adjusted_counts.get("bottom", 0)
    direction = "west-east" if west_east > north_south else "north-south"

    item = {
        'pk': pk_value,
        'timestamp': timestamp,
        'top': adjusted_counts.get("top", 0),
        'left': adjusted_counts.get("left", 0),
        'bottom': adjusted_counts.get("bottom", 0),
        'right': adjusted_counts.get("right", 0),
        'direction': direction
    }

    logger.info(f"📝 Saving to DynamoDB: {item}")
    table.put_item(Item=item)
    logger.info("✅ Data saved to DynamoDB.")

# --- Main Lambda Handler ---
def lambda_handler(event, context):
    logger.info("🚀 Lambda handler invoked.")
    try:
        images = pull_from_kinesis(event)
        for idx, img_bytes in enumerate(images):
            logger.info(f"➡️ Processing image {idx+1}")
            counts = count_blue_cars_per_lane(img_bytes)
            if counts:
                store_result_in_dynamodb(counts)
            else:
                logger.warning("⚠️ Skipping image due to decoding or processing failure.")
    except Exception as e:
        logger.error("❌ Lambda execution failed", exc_info=True)

    logger.info("✅ Lambda handler completed.")
