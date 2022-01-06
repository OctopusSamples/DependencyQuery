This script provides an example of finding the GitHub Actions build link from the latest
Octopus deployment to a given environment and then scanning artifacts created during the build
containing lists of application dependencies for specific text.

This allows teams to quickly scan the builds associated with deployed application for specific
dependencies. For example, you may wish to know what projects contain log4j dependencies in order
to assess any vulnerabilities that require your attention.

The dependencies for the script are downloaded and the script run with the example command below:

```bash
python3 -m venv my_env
. my_env/bin/activate
pip --disable-pip-version-check install -r requirements.txt
python3 main.py \
    --octopusUrl https://tenpillars.octopus.app \
    --octopusApiKey "#{ApiKey}" \
    --githubUser mcasperson \
    --githubToken "#{GitHubToken}" \
    --octopusSpace "#{Octopus.Space.Name}" \
    --octopusEnvironment "#{Octopus.Environment.Name}" \
    --octopusProject "Products Service, Audits Service, Octopub Frontend" \
    --searchText "log4j"
```