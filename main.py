# Get deployments
# Get release
# Get package
# get build info
# get build link
# get build artifact
# scan build artifact

import requests
import os
import sys
from datetime import datetime
from functools import cmp_to_key

headers = {"X-Octopus-ApiKey": os.environ['API_KEY']}
octopus_url = "https://tenpillars.octopus.app"
octopus_space = "Octopub"
octopus_environment = "Production"
octopus_project = "Audits Service"


def compare_dates(date1, date2):
    # Python 3.6 doesn't handle the colon in the timezone of a string like "2022-01-04T04:23:02.941+00:00".
    # So we need to manually strip it out.
    date1_parsed = datetime.strptime(date1["Created"][:-3] + date1["Created"][-2:], '%Y-%m-%dT%H:%M:%S.%f%z')
    date2_parsed = datetime.strptime(date2["Created"][:-3] + date2["Created"][-2:], '%Y-%m-%dT%H:%M:%S.%f%z')
    if date1_parsed < date2_parsed:
        return -1
    if date1_parsed == date2_parsed:
        return 0
    return 1


def get_space_id(space_name):
    url = octopus_url + "/api/spaces?partialName=" + space_name
    response = requests.get(url, headers=headers)
    spaces_json = response.json()
    sys.stdout.write("Response JSON: " + str(spaces_json) + "\n")

    filtered_items = [a for a in spaces_json["Items"] if a["Name"] == space_name]

    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    sys.stdout.write("Space ID: " + first_id + "\n")
    return first_id


def get_environment_id(space_id, environment_name):
    url = octopus_url + "/api/" + space_id + "/environments?partialName=" + environment_name
    response = requests.get(url, headers=headers)
    json = response.json()
    sys.stdout.write("Response JSON: " + str(json) + "\n")

    filtered_items = [a for a in json["Items"] if a["Name"] == environment_name]
    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    sys.stdout.write("Environment ID: " + first_id + "\n")
    return first_id


def get_project_id(space_id, project_name):
    url = octopus_url + "/api/" + space_id + "/projects?partialName=" + project_name
    response = requests.get(url, headers=headers)
    json = response.json()
    sys.stdout.write("Response JSON: " + str(json) + "\n")

    filtered_items = [a for a in json["Items"] if a["Name"] == project_name]
    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    sys.stdout.write("Project ID: " + first_id + "\n")
    return first_id


def get_release_id(space_id, environment_id, project_id):
    url = octopus_url + "/api/" + space_id + "/deployments?environments=" + environment_id + "&take=1000"
    response = requests.get(url, headers=headers)
    json = response.json()
    sys.stdout.write("Response JSON: " + str(json) + "\n")

    filtered_items = [a for a in json["Items"] if a["ProjectId"] == project_id]
    if len(filtered_items) == 0:
        return None

    sorted_list = sorted(filtered_items, key=cmp_to_key(compare_dates), reverse=True)
    sys.stdout.write("Response First Item: " + str(sorted_list[0]) + "\n")

    release_id = sorted_list[0]["ReleaseId"]
    sys.stdout.write("Release ID: " + release_id + "\n")

    deployment_process_id = sorted_list[0]["DeploymentProcessId"]
    sys.stdout.write("Deployment Process ID: " + deployment_process_id + "\n")

    return release_id, deployment_process_id

def get_deployment_process(space_id, deployment_process_id):
    url = octopus_url + "/api/" + space_id + "/deploymentprocesses/" + deployment_process_id
    response = requests.get(url, headers=headers)
    json = response.json()
    sys.stdout.write("Response JSON: " + str(json) + "\n")
    return json


def get_package_versions(space_id, release_id, deployment_process):
    url = octopus_url + "/api/" + space_id + "/releases/" + release_id
    response = requests.get(url, headers=headers)
    json = response.json()
    sys.stdout.write("Response JSON: " + str(json) + "\n")

    package_details = []

    packages = json["SelectedPackages"]
    for package in packages:
        step_name = package["StepName"]
        action_name = package["ActionName"]
        version = package["Version"]
        package_reference_name = package["PackageReferenceName"]

        for step in deployment_process["Steps"]:
            if step["Name"] == step_name:
                for action in step["Actions"]:
                    if action["Name"] == action_name:
                        filtered_packages = [a for a in action["Packages"] if a["Name"] == package_reference_name]
                        if len(filtered_packages) != 0:
                            package_details.append({filtered_packages[0]["PackageId"]: version})

    sys.stdout.write("Package Details: " + str(package_details) + "\n")
    return package_details


space_id = get_space_id(octopus_space)
environment_id = get_environment_id(space_id, octopus_environment)
project_id = get_project_id(space_id, octopus_project)
release_id, deployment_process_id = get_release_id(space_id, environment_id, project_id)
deployment_process = get_deployment_process(space_id, deployment_process_id)
get_package_versions(space_id, release_id, deployment_process)
