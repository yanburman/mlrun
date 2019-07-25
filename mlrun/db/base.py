# Copyright 2018 Iguazio
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

import pandas as pd
from ..utils import get_in, match_labels, dict_to_yaml, flatten
from ..render import run_to_html, runs_to_html, artifacts_to_html


class RunDBError(Exception):
    pass


class RunList(list):

    def to_rows(self):
        rows = []
        head = ['uid', 'iter', 'start', 'state', 'name', 'labels',
                'inputs', 'parameters', 'results', 'artifacts', 'error']
        for run in self:
            row = [
                get_in(run, 'metadata.uid', ''),
                get_in(run, 'metadata.iteration', ''),
                get_in(run, 'status.start_time', ''),
                get_in(run, 'status.state', ''),
                get_in(run, 'metadata.name', ''),
                get_in(run, 'metadata.labels', ''),
                get_in(run, 'spec.input_objects', ''),
                get_in(run, 'spec.parameters', ''),
                get_in(run, 'status.outputs', ''),
                get_in(run, 'status.output_artifacts', []),
                get_in(run, 'status.error', ''),
            ]
            rows.append(row)

        return [head] + rows

    def to_df(self, flat=False):
        rows = self.to_rows()
        df = pd.DataFrame(rows[1:], columns=rows[0]) #.set_index('iter')
        df['start'] = pd.to_datetime(df['start'])

        if flat:
            df = flatten(df, 'labels')
            df = flatten(df, 'parameters', 'param_')
            df = flatten(df, 'outputs', 'out_')

        return df

    def show(self, display=True):
        html = runs_to_html(self.to_df(), display)
        if not display:
            return html


class ArtifactList(list):
    def __init__(self, tag='*'):
        self.tag = tag

    def to_rows(self):
        rows = []
        head = {'tree': '', 'key': '', 'kind': '', 'path': 'target_path', 'hash': '',
                'viewer': '', 'updated': '', 'description': '', 'producer': '',
                'sources': '', 'labels': ''}
        for artifact in self:
            row = [get_in(artifact, v or k, '') for k, v in head.items()]
            rows.append(row)

        return [head.keys()] + rows

    def to_df(self, flat=False):
        rows = self.to_rows()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df['updated'] = pd.to_datetime(df['updated'], unit='s')

        if flat:
            df = flatten(df, 'producer', 'prod_')
            df = flatten(df, 'sources', 'src_')

        return df

    def show(self, display=True):
        df = self.to_df()
        if self.tag != '*':
            df.drop('tree', axis=1, inplace=True)
        html = artifacts_to_html(df, display)
        if not display:
            return html


class RunDBInterface:
    kind = ''

    def connect(self, secrets=None):
        return self

    def store_run(self, struct, uid, project='', commit=False):
        pass

    def read_run(self, uid, project=''):
        pass

    def list_runs(self, name='', project='', labels=[],
                  state='', sort=True, last=0):
        pass

    def del_run(self, uid, project=''):
        pass

    def del_runs(self, name='', project='', labels=[], state='', days_ago=0):
        pass

    def store_artifact(self, key, artifact, uid, tag='', project=''):
        pass

    def read_artifact(self, key, tag='', project=''):
        pass

    def list_artifacts(self, name='', project='', tag='', labels=[]):
        pass

    def del_artifact(self, key, tag='', project=''):
        pass

    def del_artifacts(self, name='', project='', tag='', labels=[], days_ago=0):
        pass

    def store_metric(self, keyvals={}, timestamp=None, labels={}):
        pass

    def read_metric(self, keys, query=''):
        pass
