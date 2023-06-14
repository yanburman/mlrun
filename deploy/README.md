# Deploy mlrun-api from your current code on a live system (for debugging)


In order to deploy your current code (for debugging), you need the following:

* Install automation/requirements.txt
* Install dev-requirements.txt
* Create a deploy_env.yaml based on deploy_env_template.yaml
* Add the data node/nodes to insecure registry list in your local docker config on port 8009 (see https://docs.docker.com/registry/insecure/)

