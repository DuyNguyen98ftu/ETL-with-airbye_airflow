from airflow.decorators import dag, task
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from cosmos.airflow.task_group import DbtTaskGroup
from cosmos.constants import LoadMode
from cosmos.config import RenderConfig
from include.dbt.fraud.cosmos_config import DBT_CONFIG, DBT_PROJECT_CONFIG
from airflow.models.baseoperator import chain
from datetime import datetime

AIRBYTE_JOB_LOAD_CUSTOMER_TRANSACTIONS_RAW = '5e057b43-a7d7-44ba-ac8f-430b21b7006c'
AIRBYTE_JOB_LOAD_LABELED_TRANSACTIONS_RAW = '70479436-0aee-47e4-abe9-4bfca9241488'
AIRBYTE_JOB_ID_RAW_TO_STAGING = '9d1c1a35-4ca0-4ee0-aec7-4af029fad537'

@dag(
    start_date=datetime(2024, 11, 19),
    schedule='@daily',
    catchup=False,
    tags=['airbyte', 'risk'],
)
def customer_metrics():
    # Define Airbyte tasks
    load_customer_transactions_raw = AirbyteTriggerSyncOperator(
        task_id='load_customer_transactions_raw',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_LOAD_CUSTOMER_TRANSACTIONS_RAW
    )

    load_labeled_transactions_raw = AirbyteTriggerSyncOperator(
        task_id='load_labeled_transactions_raw',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_LOAD_LABELED_TRANSACTIONS_RAW
    )

    write_to_staging = AirbyteTriggerSyncOperator(
        task_id='write_to_staging',
        airbyte_conn_id='airbyte',
        connection_id=AIRBYTE_JOB_ID_RAW_TO_STAGING
    )

    @task
    def airbyte_jobs_done():
        return True

    @task.external_python(python='/opt/airflow/soda_venv/bin/python')
    def audit_customer_transactions(scan_name='customer_transactions',
                                   checks_subpath='tables',
                                   data_source='staging'):
        from include.soda.helpers import check
        check(scan_name, checks_subpath, data_source)

    @task.external_python(python='/opt/airflow/soda_venv/bin/python')
    def audit_labeled_transactions(scan_name='labeled_transactions',
                                  checks_subpath='tables',
                                  data_source='staging'):
        from include.soda.helpers import check
        check(scan_name, checks_subpath, data_source)

    @task
    def quality_checks_done():
        return True

    # Define DBT task group
    publish = DbtTaskGroup(
        group_id='publish',
        project_config=DBT_PROJECT_CONFIG,
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=['path:models']
        )
    )

    # Chain tasks
    chain(
        [load_customer_transactions_raw, load_labeled_transactions_raw],
        write_to_staging,
        airbyte_jobs_done(),
        audit_customer_transactions(),
        audit_labeled_transactions(),
        quality_checks_done(),
        publish
    )

customer_metrics()
