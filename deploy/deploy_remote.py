#!/usr/bin/env python3
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

import io
import logging
import os
import subprocess
from typing import List

import click
import coloredlogs
import paramiko
import yaml

log_level = logging.INFO
fmt = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(level=log_level)
logger = logging.getLogger("mlrun-deploy")
coloredlogs.install(level=log_level, logger=logger, fmt=fmt)


class MlRunDeployer(object):
    class Consts(object):
        mandatory_fields = ["DATA_NODES", "USER", "PASSWORD"]
        mlrun_default_repo = "localhost:8009/quay.io/mlrun"

    def __init__(self, conf_file):
        self._config = yaml.safe_load(conf_file)
        for key in self.Consts.mandatory_fields:
            if self._config.get(key, None) is None:
                raise RuntimeError(f"Mandatory option {key} not defined")

    @staticmethod
    def _get_image_tag(branch, tag):
        return f"{tag}_{branch}"

    def _get_image_name(self, host, branch, tag):
        image_tag = self._get_image_tag(branch, tag)
        return f"{host}:8009/quay.io/mlrun/mlrun-api:{image_tag}"

    @staticmethod
    def _execute_local_proc_interactive(cmd):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            yield line
        proc.stdout.close()
        ret_code = proc.wait()
        if ret_code:
            raise subprocess.CalledProcessError(ret_code, cmd)

    def _exec_local(self, cmd: List[str], live=False) -> str:
        logger.debug("Exec local: %s", " ".join(cmd))
        buf = io.StringIO()
        for line in self._execute_local_proc_interactive(cmd):
            buf.write(line)
            if live:
                print(line, end="")
        output = buf.getvalue()
        return output

    def _exec_remote(self, cmd: List[str], live=False):
        cmd_str = " ".join(cmd)

        logger.debug("Exec remote: %s", cmd_str)

        stdin_stream, stdout_stream, stderr_stream = self._ssh_client.exec_command(
            cmd_str
        )

        stdout = ""
        if live:
            while True:
                line = stdout_stream.readline()
                stdout += line
                if not line:
                    break
                print(line, end="")
        else:
            stdout = stdout_stream.read()

        stderr = stderr_stream.read().decode("utf8")

        exit_status = stdout_stream.channel.recv_exit_status()

        if exit_status:
            raise RuntimeError(
                f"Command '{cmd_str}' finished with failure ({exit_status})\n{stderr}"
            )

    def _find_latest_git_tag(self) -> str:
        cmd = ["git", "describe", "--tags"]

        return self._exec_local(cmd).strip()

    def _find_current_git_branch(self) -> str:
        cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        return self._exec_local(cmd).strip()

    def _make_mlrun_api(self, image_tag):
        logger.info("Building mlrun-api docker image")
        os.environ["MLRUN_VERSION"] = image_tag
        os.environ["MLRUN_DOCKER_REPO"] = self.Consts.mlrun_default_repo
        cmd = ["make", "api"]
        return self._exec_local(cmd, live=True).strip()

    def _connect_to_node(self, node):
        logger.debug(f"Connecting to {node}")

        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy)
        self._ssh_client.connect(
            node,
            username=self._config["USER"],
            password=self._config["PASSWORD"],
        )

    def _disconnect_from_node(self):
        self._ssh_client.close()

    def do_replacing(self):
        branch = self._find_current_git_branch()
        tag = self._find_latest_git_tag()

        nodes = self._config["DATA_NODES"]
        if not isinstance(nodes, list):
            nodes = [nodes]

        self._make_mlrun_api(self._get_image_tag(branch, tag))
        built_image = self._get_image_name("localhost", branch, tag)

        for node in nodes:
            node_image_name = self._get_image_name(node, branch, tag)
            self._exec_local(["docker", "tag", built_image, node_image_name])

            self._connect_to_node(node)
            try:
                try:
                    logger.info(f"Pushing mlrun-api docker image to {node}")
                    self._exec_local(
                        [
                            "docker",
                            "push",
                            node_image_name,
                        ],
                        live=True,
                    )
                except subprocess.CalledProcessError:
                    logger.critical(
                        f"Make sure you have added {nodes} to docker config of insecure registries on port 8009. See https://docs.docker.com/registry/insecure/ for details"
                    )
                    raise

                logger.info(f"Replacing mlrun-api-chief on {node}")
                self._exec_remote(
                    [
                        "kubectl",
                        "-n",
                        "default-tenant",
                        "patch",
                        "deployment",
                        "mlrun-api-chief",
                        "-p",
                        """'{"spec":{"template":{"spec":{"containers":[{"name":"mlrun-api","imagePullPolicy":"Always"}]}}}}'""",
                    ]
                )
                logger.info(f"Replacing mlrun-api-worker on {node}")
                self._exec_remote(
                    [
                        "kubectl",
                        "-n",
                        "default-tenant",
                        "patch",
                        "deployment",
                        "mlrun-api-worker",
                        "-p",
                        """'{"spec":{"template":{"spec":{"containers":[{"name":"mlrun-api","imagePullPolicy":"Always"}]}}}}'""",
                    ]
                )
                logger.info(f"Restarting mlrun-api on {node}")
                self._exec_remote(
                    [
                        "kubectl",
                        "-n",
                        "default-tenant",
                        "rollout",
                        "restart",
                        "deployment",
                        "mlrun-api-chief",
                        "mlrun-api-worker",
                    ]
                )
                logger.info(f"Waiting for mlrun-api to become ready on {node}")
                self._exec_remote(
                    [
                        "kubectl",
                        "-n",
                        "default-tenant",
                        "wait",
                        "pods",
                        "-l",
                        "app.kubernetes.io/name=mlrun",
                        "--for",
                        "condition=Ready",
                        "--timeout=90s",
                    ]
                )
            finally:
                self._disconnect_from_node()
                try:
                    self._exec_local(["docker", "rmi", node_image_name])
                except subprocess.CalledProcessError:
                    pass

        logger.info("Deployed branch successfully! Yay!")


@click.command(help="mlrun-api deployer to remote system")
@click.option("--verbose", is_flag=True, help="Print what we are doing")
@click.option(
    "-c",
    "--config",
    help="Config file",
    default="deploy/deploy_env.yml",
    type=click.File(mode="r"),
    show_default=True,
)
def main(verbose, config):
    if verbose:
        coloredlogs.set_level(logging.DEBUG)

    MlRunDeployer(config).do_replacing()


if __name__ == "__main__":
    main()
