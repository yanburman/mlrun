# Copyright 2023 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json


def init_context(context):
    context.user_data.data_list = []


def handler(context, event):
    event_data = event.body

    # Extract the operation and data from the event data
    operation = event_data.get("operation")
    data = event_data.get("data")

    # Perform actions based on the provided operation
    if operation == "add":
        context.user_data.data_list.append(data)
        response = {"message": "Object added successfully", "status_code": 200}

    elif operation == "get":
        if context.user_data.data_list:
            element = context.user_data.data_list[0]
            response = {"element": element, "status_code": 200}
        else:
            response = {"message": "List is empty", "status_code": 400}

    elif operation == "delete":
        if context.user_data.data_list:
            deleted_element = context.user_data.data_list.pop(0)
            response = {
                "message": f"First element '{deleted_element}' deleted",
                "status_code": 200,
            }
        else:
            response = {"message": "List is empty", "status_code": 400}

    elif operation == "list":
        response = {"data_list": context.user_data.data_list, "status_code": 200}

    elif operation == "reset":
        context.user_data.data_list.clear()
        response = {"message": "List was reset successfully", "status_code": 200}

    else:
        response = {"message": "Invalid operation", "status_code": 400}

    return json.dumps(response)
