import requests
import os
import sys
from datetime import datetime
from functools import cmp_to_key
from requests.auth import HTTPBasicAuth
import tempfile
from requests import get
import zipfile

headers = {"X-Octopus-ApiKey": os.environ['API_KEY']}
github_auth = HTTPBasicAuth(os.environ['GITHUB_USER'], os.environ['GITHUB_TOKEN'])
octopus_url = "https://tenpillars.octopus.app"
octopus_space = "Octopub"
octopus_environment = "Production"
octopus_project = "Audits Service"
github_dependencies_artifact_name = "Dependencies"


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
    url = octopus_url + "/api/spaces?partialName=" + space_name + "&take=1000"
    response = requests.get(url, headers=headers)
    spaces_json = response.json()

    filtered_items = [a for a in spaces_json["Items"] if a["Name"] == space_name]

    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    return first_id


def get_environment_id(space_id, environment_name):
    url = octopus_url + "/api/" + space_id + "/environments?partialName=" + environment_name + "&take=1000"
    response = requests.get(url, headers=headers)
    json = response.json()

    filtered_items = [a for a in json["Items"] if a["Name"] == environment_name]
    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    return first_id


def get_project_id(space_id, project_name):
    url = octopus_url + "/api/" + space_id + "/projects?partialName=" + project_name + "&take=1000"
    response = requests.get(url, headers=headers)
    json = response.json()

    filtered_items = [a for a in json["Items"] if a["Name"] == project_name]
    if len(filtered_items) == 0:
        return None

    first_id = filtered_items[0]["Id"]
    return first_id


def get_release_id(space_id, environment_id, project_id):
    url = octopus_url + "/api/" + space_id + "/deployments?environments=" + environment_id + "&take=1000"
    response = requests.get(url, headers=headers)
    json = response.json()

    filtered_items = [a for a in json["Items"] if a["ProjectId"] == project_id]
    if len(filtered_items) == 0:
        return None

    sorted_list = sorted(filtered_items, key=cmp_to_key(compare_dates), reverse=True)
    release_id = sorted_list[0]["ReleaseId"]

    return release_id


def get_build_urls(space_id, release_id):
    url = octopus_url + "/api/" + space_id + "/releases/" + release_id
    response = requests.get(url, headers=headers)
    json = response.json()

    build_information_with_urls = [a for a in json["BuildInformation"] if "github.com" in a["BuildUrl"]]
    build_urls = list(map(lambda b: b["BuildUrl"], build_information_with_urls))

    if len(build_urls) == 0:
        sys.stdout.write("No build information results contained build URLs to GitHub.\n")
        sys.stdout.write("This script assumes GitHub Actions were used to build the packages deployed by Octopus.\n")

    return build_urls


def download_file(url):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
        # get request
        response = get(url, auth=github_auth)
        # write to file
        tmp_file.write(response.content)
        return tmp_file.name


def get_artifacts(build_urls, dependency_artifact_name):
    files = []

    for url in build_urls:
        # turn https://github.com/OctopusSamples/OctoPub/actions/runs/1660462851 into
        # https://api.github.com/repos/OctopusSamples/OctoPub/actions/runs/1660462851/artifacts
        artifacts_api_url = url.replace("github.com", "api.github.com/repos") + "/artifacts"
        response = get(artifacts_api_url, auth=github_auth)
        artifact_json = response.json()

        filtered_items = [a for a in artifact_json["artifacts"] if a["name"] == dependency_artifact_name]

        if len(filtered_items) == 0:
            sys.stdout.write("No artifacts were found in the GitHub Action run called " + dependency_artifact_name + "\n")

        for artifact in filtered_items:
            artifact_url = artifact["archive_download_url"]
            files.append(download_file(artifact_url))

    return files


def unzip_files(zip_files):
    text_files = []
    for file in zip_files:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_ref.extractall(tmp_dir)
                for extracted_file in os.listdir(tmp_dir):
                    filename = os.fsdecode(extracted_file)
                    if filename.endswith(".txt"):
                        with open(os.path.join(tmp_dir, extracted_file)) as f:
                            content = f.read()
                            text_files.append(content)
                            sys.stdout.write(content)
    return text_files


def scan_dependencies():
    space_id = get_space_id(octopus_space)
    environment_id = get_environment_id(space_id, octopus_environment)
    project_id = get_project_id(space_id, octopus_project)
    release_id = get_release_id(space_id, environment_id, project_id)
    urls = get_build_urls(space_id, release_id)
    files = get_artifacts(urls, github_dependencies_artifact_name)
    text_files = unzip_files(files)


scan_dependencies()
