# Weather Data Pipeline

![Flow Diagram](https://github.com/VincentRevel/Weather-DAG-Airflow/blob/main/Project%20Flow%20Diagram.png)

## Overview

This repository contains the code and documentation for a data pipeline that retrieves today's weather data from the OpenWeather API, processes it, and stores it in an AWS RDS Postgres database. Additionally, the pipeline integrates data from an Amazon S3 bucket to enrich the weather information. The entire process is orchestrated using Apache Airflow on an AWS EC2 instance.

## Tech Stack

The project utilizes the following technologies and tools:

- **Programming Languages**: Python
- **Data Processing Libraries**: Pandas
- **Database**: AWS RDS Postgres
- **Cloud Services**: Amazon Web Services (AWS)
- **Orchestration**: Apache Airflow

## Getting Started

To set up and run the data pipeline, follow these steps:

1. **Prerequisites**: Make sure you have the necessary AWS credentials and an AWS RDS Postgres instance set up. Also, ensure you have Python and the required packages installed.

2. **Configuration**: Update the configuration files with your AWS and database connection details.

3. **Run the Pipeline**: Ensure that Apache Airflow is up and running on your AWS EC2 instance.

4. **Monitoring**: Monitor the pipeline's progress and logs using the Apache Airflow web interface.

## Challenges Faced
Building such a data pipeline alone came with its fair share of challenges. One notable challenge I encountered during this project was dealing with AWS limitations, particularly with educational/student accounts. These accounts often have restrictions on creating IAM policies and roles, making it challenging to provide direct access from Postgres to the S3 bucket.
To work around this limitation, I opted for an alternative approach. Instead of granting direct access, I downloaded the CSV files from the S3 bucket into the EC2 instance locally. Subsequently, these files were converted into tables and loaded into the AWS RDS Postgres database. While this introduced an extra step, it allowed me to navigate the limitations effectively and complete the project successfully.

## Documentation

Detailed documentation for this project, including a step-by-step guide and explanations of the code, can be found in my [Medium post](https://medium.com/@vincentrevell/building-a-data-pipeline-for-weather-data-using-aws-and-apache-airflow-a-solo-journey-cea868adb54c).

## Acknowledgments

- [OpenWeather API](https://openweathermap.org/api): The source of weather data used in this project.
- [Apache Airflow](https://airflow.apache.org/): Used for orchestrating and automating the data pipeline.
- [Amazon Web Services (AWS)](https://aws.amazon.com/): Cloud services used for data storage and processing.
