from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.http.sensors.http import HttpSensor
import json
from airflow.providers.http.operators.http import SimpleHttpOperator
import boto3
import psycopg2
import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook

def kelvin_to_fahrenheit(temp_in_kelvin):
    temp_in_fahrenheit = (temp_in_kelvin - 273.15) * (9/5) + 32
    return round(temp_in_fahrenheit, 3)

def transform_load_data(task_instance):
    data = task_instance.xcom_pull(task_ids="parallel_processing.exctract_weather_data_task")
    
    city = data["name"]
    weather_description = data["weather"][0]['description']
    temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp"])
    feels_like_farenheit= kelvin_to_fahrenheit(data["main"]["feels_like"])
    min_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_min"])
    max_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_max"])
    pressure = data["main"]["pressure"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    time_of_record = datetime.utcfromtimestamp(data['dt'] + data['timezone'])
    sunrise_time = datetime.utcfromtimestamp(data['sys']['sunrise'] + data['timezone'])
    sunset_time = datetime.utcfromtimestamp(data['sys']['sunset'] + data['timezone'])

    transformed_data = {"city": city,
                        "description": weather_description,
                        "temperature_farenheit": temp_farenheit,
                        "feels_like_farenheit": feels_like_farenheit,
                        "minimun_temp_farenheit":min_temp_farenheit,
                        "maximum_temp_farenheit": max_temp_farenheit,
                        "pressure": pressure,
                        "humidity": humidity,
                        "wind_speed": wind_speed,
                        "time_of_record": time_of_record,
                        "sunrise_local_time)":sunrise_time,
                        "sunset_local_time)": sunset_time                        
                        }
    transformed_data_list = [transformed_data]
    df_data = pd.DataFrame(transformed_data_list)
    
    df_data.to_csv("current_weather_data.csv", index=False, header=False)

def load_weather():
    hook = PostgresHook(postgres_conn_id= 'postgres_conn')
    hook.copy_expert(
        sql= "COPY weather_data FROM stdin WITH DELIMITER as ','",
        filename='current_weather_data.csv'
    )

def save_joined_data_s3(task_instance):
    data = task_instance.xcom_pull(task_ids="task_join_data")
    df = pd.DataFrame(data, columns = ['city', 'description', 'temperature_farenheit', 'feels_like_farenheit', 'minimun_temp_farenheit', 'maximum_temp_farenheit', 'pressure','humidity', 'wind_speed', 'time_of_record', 'sunrise_local_time', 'sunset_local_time', 'state', 'census_2020', 'land_area_sq_mile_2020'])
    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    dt_string = 'joined_weather_data_' + dt_string
    df.to_csv(f"s3://airflow-weather-bucket/{dt_string}.csv", index=False)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 12),
    'email': ['*******@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}

with DAG('weather_dag',
        default_args=default_args,
        schedule_interval = '@daily',
        catchup=False) as dag:

        start_pipeline = DummyOperator(
            task_id = 'start_pipeline'
        )

        join_data = PostgresOperator(
                task_id='join_data_task',
                postgres_conn_id = "postgres_conn",
                sql= '''SELECT 
                    w.city,                    
                    description,
                    temperature_farenheit,
                    feels_like_farenheit,
                    minimun_temp_farenheit,
                    maximum_temp_farenheit,
                    pressure,
                    humidity,
                    wind_speed,
                    time_of_record,
                    sunrise_local_time,
                    sunset_local_time,
                    state,
                    census_2020,
                    land_area_sq_mile_2020                    
                    FROM weather_data w
                    INNER JOIN city_look_up c
                        ON w.city = c.city                                      
                ;
                '''
        )

        load_joined_data = PythonOperator(
            task_id= 'join_data_to_bucket',
            python_callable=save_joined_data_s3
        )

        end_pipeline = DummyOperator(
                task_id = 'end_pipeline'
        )

        with TaskGroup(group_id = 'parallel_processing', tooltip= "Extract_from_S3_and_weatherapi") as parallel_processing:
            create_table_task = PostgresOperator(
                task_id='create_table_local_task',
                postgres_conn_id="postgres_conn",
                sql='''  
                    CREATE TABLE IF NOT EXISTS city_look_up (
                        city TEXT NOT NULL,
                        state TEXT NOT NULL,
                        census_2020 INT NOT NULL,  -- Change the data type to INT
                        land_Area_sq_mile_2020 NUMERIC NOT NULL
                    );
                '''
            )

            truncate_table_task = PostgresOperator(
                task_id='truncate_table_local_task',
                postgres_conn_id="postgres_conn",
                sql='''TRUNCATE TABLE city_look_up;'''
            )
            def download_csv_from_s3():
                s3_bucket_name = 'airflow-weather-bucket'
                s3_object_key = 'us_city.csv'
                local_file_path = '/home/ubuntu/data/local_file.csv'

                s3 = boto3.client('s3', region_name='us-east-1')
                s3.download_file(s3_bucket_name, s3_object_key, local_file_path)

            download_csv_task = PythonOperator(
                task_id='download_csv_to_VM_task',
                python_callable=download_csv_from_s3,
                dag=dag,
            )

            def transfer_data_to_postgres():
                csv_file_path = '/home/ubuntu/data/local_file.csv'

                hook = PostgresHook(postgres_conn_id='postgres_conn')

                copy_sql = f"""
                    COPY city_look_up FROM stdin WITH
                    CSV HEADER
                    DELIMITER as ','
                """
                hook.copy_expert(
                    sql=copy_sql,
                    filename=csv_file_path
                )

            transfer_data_task = PythonOperator(
                task_id='local_to_postgres_task',
                python_callable=transfer_data_to_postgres,
                dag=dag,
            )
            
            create_table_weather = PostgresOperator(
                task_id='create_table_weather_task',
                postgres_conn_id = "postgres_conn",
                sql= ''' 
                    CREATE TABLE IF NOT EXISTS weather_data (
                    city TEXT,
                    description TEXT,
                    temperature_farenheit NUMERIC,
                    feels_like_farenheit NUMERIC,
                    minimun_temp_farenheit NUMERIC,
                    maximum_temp_farenheit NUMERIC,
                    pressure NUMERIC,
                    humidity NUMERIC,
                    wind_speed NUMERIC,
                    time_of_record TIMESTAMP,
                    sunrise_local_time TIMESTAMP,
                    sunset_local_time TIMESTAMP                    
                );
                '''
            )

            is_weather_api_ready = HttpSensor(
                task_id ='check_weather_api_task',
                http_conn_id='weathermap_api',
                endpoint='/data/2.5/weather?q=malang&APPID=********************************'
            )

            extract_weather_data = SimpleHttpOperator(
                task_id = 'exctract_weather_data_task',
                http_conn_id = 'weathermap_api',
                endpoint='/data/2.5/weather?q=malang&APPID==********************************',
                method = 'GET',
                response_filter= lambda r: json.loads(r.text),
                log_response=True
            )

            transform_load_weather_data = PythonOperator(
                task_id= 'transform_weather_data_task',
                python_callable=transform_load_data
            )

            load_weather_data = PythonOperator(
                task_id= 'load_weather_data_task',
                python_callable=load_weather
            )
            # Extract and load data from S3 Bucket to AWS RDG Postgres
            download_csv_task >> create_table_task >> truncate_table_task >> transfer_data_task
            # Extact, transform, and load data from OpenWeather API to AWS RDG Postgres
            create_table_weather >> is_weather_api_ready >> extract_weather_data >> transform_load_weather_data >> load_weather_data
        start_pipeline >> parallel_processing >> join_data >> load_joined_data >> end_pipeline