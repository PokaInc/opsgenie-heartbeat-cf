import json
import os
import uuid
from botocore.vendored import requests

SUCCESS = "SUCCESS"
FAILED = "FAILED"


class HeartbeatAlreadyExistsError(Exception):
    def __init__(self, name):
        self.message = f'Heartbeat already exists: {name}'
        super().__init__(self.message)

class UnexistingHeartbeatError(Exception):
    def __init__(self, name):
        self.message = f'Unexisting heartbeat: {name}'
        super().__init__(self.message)


def lambda_handler(event, context):
    try:
        _lambda_handler(event, context)
    except Exception as e:
        # Must raise, otherwise the Lambda will be marked as successful, and the exception
        # will not be logged to CloudWatch logs.
        send(
            event,
            context,
            response_status=FAILED,
            # Do not fail on delete to avoid rollback failure
            response_data=None,
            physical_resource_id=event.get('PhysicalResourceId', str(uuid.uuid4())),
            reason=e
        )
        raise


def _lambda_handler(event, context):
    print("Received event: ")
    print(event)

    resource_type = event['ResourceType']
    request_type = event['RequestType']
    resource_properties = event['ResourceProperties']
    name = resource_properties['Name']
    opsgenie_heartbeat_api_key = os.environ['OPSGENIE_HEARTBEAT_API_KEY']

    def _create():
        print('Calling _create()')
        create_kwargs = dict(
            name=name,
            api_key=opsgenie_heartbeat_api_key,
        )
        if 'Interval' in resource_properties:
            create_kwargs['interval'] = resource_properties['Interval']
        if 'IntervalUnit' in resource_properties:
            create_kwargs['interval_unit'] = resource_properties['IntervalUnit']
        if 'Description' in resource_properties:
            create_kwargs['description'] = resource_properties['Description']
        if 'Enabled' in resource_properties:
            create_kwargs['enabled'] = resource_properties['Enabled']
        create_heartbeat(**create_kwargs)

    def _update():
        print('Calling _update()')
        update_kwargs = dict(
            name=name,
            api_key=opsgenie_heartbeat_api_key,
        )
        if 'Interval' in resource_properties:
            update_kwargs['interval'] = resource_properties['Interval']
        if 'IntervalUnit' in resource_properties:
            update_kwargs['interval_unit'] = resource_properties['IntervalUnit']
        if 'Description' in resource_properties:
            update_kwargs['description'] = resource_properties['Description']
        if 'Enabled' in resource_properties:
            update_kwargs['enabled'] = resource_properties['Enabled']
        update_heartbeat(**update_kwargs)

    if resource_type == "Custom::OpsGenieHeartbeat":
        if request_type == 'Create':
            _create()

        elif request_type == 'Update':
            old_resource_properties = event['OldResourceProperties']
            old_name = old_resource_properties['Name']
            print(f'name: {name}')
            print(f'old_name: {old_name}')

            if old_name == name:
                _update()
            else:
                if name == event['PhysicalResourceId']:
                    print('Detected UPDATE triggered by rollback')
                    _update()
                else:
                    _create()

        elif request_type == 'Delete':
            if name == event['PhysicalResourceId']:
                delete_heartbeat(name=name, api_key=opsgenie_heartbeat_api_key)
            else:
                print('Not deleting heartbeat, since stack has never been succesfully created')

        else:
            print('Request type is {request_type}, doing nothing.'.format(request_type=request_type))

    else:
        raise ValueError("Unexpected resource_type: {resource_type}".format(resource_type=resource_type))

    send(
        event,
        context,
        response_status=SUCCESS,
        response_data={'Name': name},
        physical_resource_id=name,
    )


def create_heartbeat(name, api_key, interval=None, interval_unit=None, description=None, enabled=True):
    if _heartbeat_exists(name=name, api_key=api_key):
        raise HeartbeatAlreadyExistsError(name=name)

    response = requests.post(
        'https://api.opsgenie.com/v1/json/heartbeat',
        json=dict(
            apiKey=api_key,
            name=name,
            interval=interval,
            intervalUnit=interval_unit,
            description=description,
            enabled=enabled,
        ))
    try:
        response.raise_for_status()
    except:
        print(response.content)
        raise


def update_heartbeat(name, api_key, interval=None, interval_unit=None, description=None, enabled=True):
    response = requests.post(
        'https://api.opsgenie.com/v1/json/heartbeat',
        json=dict(
            apiKey=api_key,
            name=name,
            interval=interval,
            intervalUnit=interval_unit,
            description=description,
            enabled=enabled,
        ))
    try:
        response.raise_for_status()
    except:
        print(response.content)
        raise


def delete_heartbeat(name, api_key):
    print('calling delete_heartbeat()')
    if not _heartbeat_exists(name=name, api_key=api_key):
        raise UnexistingHeartbeatError(name=name)

    response = requests.delete(
        'https://api.opsgenie.com/v1/json/heartbeat',
        params=dict(
            apiKey=api_key,
            name=name,
        ))
    try:
        response.raise_for_status()
    except:
        print(response.content)
        raise

def _heartbeat_exists(name, api_key):
    response = requests.get(
        'https://api.opsgenie.com/v1/json/heartbeat',
        params=dict(
            name=name,
            apiKey=api_key,
        )
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e :
        if e.response.status_code == 400 and \
                f'Heartbeat with name [{name}] does not exist' in response.json()['error']:
            return False
        else:
            raise
    else:
        return True

def send(event, context, response_status, response_data, physical_resource_id, reason=None):
    response_url = event['ResponseURL']

    response_body = {
        'Status': response_status,
        'Reason': str(reason) if reason else 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
        'PhysicalResourceId': physical_resource_id,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data,
    }

    json_response_body = json.dumps(response_body)

    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        requests.put(
            response_url,
            data=json_response_body,
            headers=headers
        )
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))
