# Plateforme intelligente de gestion du trafic routier

## Summary

Developed an intelligent traffic management system with real-time vehicle detection and dynamic light control using AWS and simulation tools. Key components include:

- Simulated traffic with **SUMO** on AWS EC2 and streamed screenshots every 5 simulation steps via **Flask** and **TraCI**.
- Used **AWS Kinesis** for real-time image streaming; images processed with **OpenCV** in **AWS Lambda** to estimate vehicle counts.
- Triggered Lambda functions to update traffic lights based on analysis, applying decisions live in the simulation via Flask.

## Technologies Used

- Python  
- Flask  
- SUMO  
- TraCI  
- OpenCV  
- AWS EC2  
- AWS Lambda  
- AWS Kinesis  
- DynamoDB  
- Terraform  

## Deployment

The infrastructure is provisioned using **Terraform**, which automates the following resources:

- Creation of a **VPC** to isolate the environment.
- Provisioning of an **EC2 instance** to host the SUMO simulation and Flask application.
- Configuration of **AWS Lambda** functions for image processing and traffic light control.
- Use of **AWS Kinesis** for real-time image streaming.
- Storage of Terraform backend state securely in an **S3 bucket** with state locking enabled.
- Setup of **DynamoDB** tables for storing vehicle count and traffic signal data.
- Configuration of **IAM roles and policies** to securely grant necessary permissions to Lambda functions, EC2 instances, and Kinesis streams.

This setup ensures a scalable, secure, and reproducible deployment environment.

## SUMO Simulation Preview

> ![sumo-simulation](https://github.com/user-attachments/assets/61a08eef-9586-4726-bf64-f483f65500c1)

## Project Architecture

Below is the architecture diagram illustrating the components and data flow of the intelligent traffic management platform:

> ![project-architecture](https://github.com/user-attachments/assets/04f08cee-3eb9-4599-9e39-78107f80f064)





---




