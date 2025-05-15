terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 4.55" # Replace with your desired version
        }
    }

    required_version = ">= 1.3.0" # Replace with your desired Terraform version
}

provider "aws" {
  region = "us-east-1"
}

# 1. VPC Setup
resource "aws_vpc" "traffic_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = {
    Name = "TrafficLight-VPC"
  }
}

# 2. Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.traffic_vpc.id
  tags = {
    Name = "TrafficLight-IGW"
  }
}

# 3. Public Subnet
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.traffic_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  tags = {
    Name = "Public-Subnet"
  }
}

# 4. Route Table for Public Access
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.traffic_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = {
    Name = "Public-RouteTable"
  }
}

resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

# 5. EC2 Spot Instance for SUMO
resource "aws_spot_instance_request" "sumo_simulator" {
  ami           = "ami-0c55b159cbfafe1f0" # Ubuntu 22.04 LTS
  instance_type = "t3.medium"
  spot_price    = "0.02" # ~$0.02/hour
  wait_for_fulfillment = true
  subnet_id     = aws_subnet.public.id
  associate_public_ip_address = true

  tags = {
    Name = "SUMO-Simulator"
  }

  # Install SUMO on startup
  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y sumo sumo-tools python3-pip
              pip3 install boto3
              EOF
}

# 6. S3 Bucket for Models/Data
resource "aws_s3_bucket" "traffic_data" {
  bucket = "traffic-sim-data-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 7. DynamoDB for Traffic Light States
resource "aws_dynamodb_table" "traffic_states" {
  name         = "TrafficLightStates"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "intersection_id"

  attribute {
    name = "intersection_id"
    type = "S"
  }
}

# 8. Kinesis Data Stream
resource "aws_kinesis_stream" "traffic_stream" {
  name             = "TrafficDataStream"
  shard_count      = 1
  retention_period = 24 # Hours
}

# 9. Lambda Function for Processing
resource "aws_lambda_function" "traffic_processor" {
  function_name = "TrafficDataProcessor"
  runtime       = "python3.9"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
  filename      = "lambda_function.zip" # Your packaged Lambda code

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.traffic_states.name
      KINESIS_STREAM = aws_kinesis_stream.traffic_stream.name
    }
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_access" {
  name = "lambda_access_policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "kinesis:PutRecord",
          "s3:GetObject"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

# Outputs
output "sumo_public_ip" {
  value = aws_spot_instance_request.sumo_simulator.public_ip
}

output "kinesis_stream_name" {
  value = aws_kinesis_stream.traffic_stream.name
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.traffic_states.name
}