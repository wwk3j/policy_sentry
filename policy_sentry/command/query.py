import click
import json
from policy_sentry.shared.query import query_condition_table, query_condition_table_by_name, \
    query_arn_table_for_raw_arns, query_arn_table_by_name, query_action_table, query_action_table_by_name, \
    query_action_table_by_access_level, query_action_table_by_arn_type_and_access_level, \
    query_action_table_for_all_condition_key_matches, query_action_table_for_actions_supporting_wildcards_only, \
    query_arn_table_for_arn_types
from policy_sentry.shared.database import connect_db
from policy_sentry.shared.actions import transform_access_level_text
from pathlib import Path

HOME = str(Path.home())
CONFIG_DIRECTORY = '/.policy_sentry/'
DATABASE_FILE_NAME = 'aws.sqlite3'
database_file_path = HOME + CONFIG_DIRECTORY + DATABASE_FILE_NAME


@click.command(
    short_help="Allow users to query the action, arn, and condition tables from command line."
)
@click.option(
    '--table',
    type=click.Choice(['action', 'arn', 'condition']),
    required=True,
    help='The table to query. Accepted values are action, arn, or condition.'
)
@click.option(
    '--service',
    type=str,
    required=True,
    help="Filter according to AWS service."
)
@click.option(
    '--name',
    type=str,
    required=False,
    help='Name of the action, arn type, or condition key. Optional.'
)
@click.option(
    '--access-level',
    type=click.Choice(['read', 'write', 'list', 'tagging', 'permissions-management']),
    required=False,
    help='If action table is chosen, you can use this to filter according to CRUD levels. '
         'Acceptable values are read, write, list, tagging, permissions-management'
)
@click.option(
    '--condition',
    type=str,
    required=False,
    help='If action table is chosen, you can supply a condition key to show a list of all IAM actions that'
         ' support the condition key.'
)
@click.option(
    '--wildcard-only',
    is_flag=True,
    required=False,
    help='If action table is chosen, show the IAM actions that only support '
         'wildcard resources - i.e., cannot support ARNs in the resource block.'
)
@click.option(
    '--list-arn-types',
    is_flag=True,
    required=False,
    help='If ARN table is chosen, show the short names of ARN Types.'
)
# TODO: Ask Matty about how to handle Click context
#  so we can have different options for filtering based on which table the user selects
def query(table, service, name, access_level, condition, wildcard_only, list_arn_types):
    """Allow users to query the action tables, arn tables, and condition keys tables from command line."""
    db_session = connect_db(database_file_path)
    if table == 'condition':
        # Get a list of all condition keys available to the service
        if name is None:
            condition_results = query_condition_table(db_session, service)
            for item in condition_results:
                print(item)
        # Get details on the specific condition key
        else:
            output = query_condition_table_by_name(db_session, service, name)
            print(json.dumps(output, indent=4))
    elif table == 'arn':
        # Get a list of all RAW ARN formats available through the service.
        if name is None and list_arn_types is None:
            raw_arns = query_arn_table_for_raw_arns(db_session, service)
            for item in raw_arns:
                print(item)
        # Get a list of all the ARN types per service, paired with the RAW ARNs
        elif name is None and list_arn_types:
            output = query_arn_table_for_arn_types(db_session, service)
            print(json.dumps(output, indent=4))
        # Get the raw ARN format for the `cloud9` service with the short name `environment`
        else:
            output = query_arn_table_by_name(db_session, service, name)
            print(json.dumps(output, indent=4))
    elif table == 'action':
        # Get a list of all IAM Actions available to the service
        if name is None and access_level is None and condition is None and wildcard_only is None:
            action_list = query_action_table(db_session, service)
            print(f"ALL {service} actions:")
            for item in action_list:
                print(item)
        # Get a list of all IAM actions under the service that have the specified access level.
        elif name is None and access_level:
            level = transform_access_level_text(access_level)
            output = query_action_table_by_access_level(db_session, service, level)
            print(f"Service: {service}")
            print(f"Access level: \"{level}\"")
            print("Actions:")
            print(json.dumps(output, indent=4))
        # Get a list of all IAM actions under the service that support the specified condition key.
        elif condition:
            print(f"IAM actions under {service} service that support the {condition} condition only:")
            output = query_action_table_for_all_condition_key_matches(db_session, service, condition)
            print(json.dumps(output, indent=4))
        # Get a list of IAM Actions under the service that only support resources = "*"
        # (i.e., you cannot restrict it according to ARN)
        elif wildcard_only:
            print(f"IAM actions under {service} service that support wildcard resource values only:")
            output = query_action_table_for_actions_supporting_wildcards_only(db_session, service)
            print(json.dumps(output, indent=4))
        elif name and access_level is None:
            output = query_action_table_by_name(db_session, service, name)
            print(json.dumps(output, indent=4))
        else:
            print("Unknown error for query command - this error should not happen.")
    else:
        print("Table name not valid.")
