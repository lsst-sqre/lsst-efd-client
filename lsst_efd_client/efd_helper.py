# This file is part of jupyterlabutils.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import aioinflux
from functools import partial
import logging
import pandas as pd
from astropy.time import Time, TimeDelta

from .auth_helper import NotebookAuth


class EfdClient:
    """Class to handle connections and basic queries"""
    subclasses = {}
    deployment = ''

    def __init__(self, efd_name, db_name='efd', port='443',
                 internal_scale='tai', path_to_creds='~/.lsst/notebook_auth.yaml'):
        self.db_name = db_name
        self.internal_scale = internal_scale
        self.auth = NotebookAuth(path=path_to_creds)
        host, user, password = self.auth.get_auth(efd_name)
        self.influx_client = aioinflux.InfluxDBClient(host=host,
                                                      port=port,
                                                      ssl=True,
                                                      username=user,
                                                      password=password,
                                                      db=db_name,
                                                      mode='async')  # mode='blocking')
        self.influx_client.output = 'dataframe'
        self.query_history = []

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Register subclasses with the abstract base class"""
        super().__init_subclass__(**kwargs)
        if cls.mode in EfdClient.subclasses:
            raise ValueError(f'Class for mode, {cls.mode}, already defined')
        EfdClient.subclasses[cls.deployment] = cls

    def from_name(self, efd_name, *args, **kwargs):
        if efd_name not in self. subclasses:
            raise NotImplementedError(f'There is no EFD client class implemented for {efd_name}.')
        return self.subclasses[efd_name](efd_name, *args, **kwargs)

    async def _do_query(self, query):
        self.query_history.append(query)
        result = await self.influx_client.query(query)
        return result

    async def get_topics(self):
        topics = await self._do_query('SHOW MEASUREMENTS')
        return topics['name'].tolist()

    async def get_fields(self, topic_name):
        fields = await self._do_query(f'SHOW FIELD KEYS FROM "{self.db_name}"."autogen"."{topic_name}"')
        return fields['fieldKey'].tolist()

    def build_time_range_query(self, topic_name, fields, start, end, is_window=False, index=None):
        ''' Build the query '''
        if not isinstance(start, Time):
            raise TypeError('The first time argument must be a time stamp')

        if not start.scale == self.internal_scale:
            logging.warn(f'Timestamps must be in {self.internal_scale.upper()}.  Converting...')
            start = getattr(start, self.internal_scale)

        if isinstance(end, TimeDelta):
            if is_window:
                start_str = (start - end/2).isot
                end_str = (start + end/2).isot
            else:
                start_str = start.isot
                end_str = (start + end).isot
        elif isinstance(end, Time):
            end = getattr(end, self.internal_scale)
            start_str = start.isot
            end_str = end.isot
        else:
            raise TypeError('The second time argument must be the time stamp for the end ' +
                            'or a time delta.')
        index_str = ''
        if index:
            parts = topic_name.split('.')
            index_str = f' AND {parts[-2]}ID = {index}'  # The CSC name is always the penultimate in the namespace
        timespan = f"time >= '{start_str}Z' AND time <= '{end_str}Z'{index_str}"  # influxdb demands the trailing Z

        if isinstance(fields, str):
            fields = [fields, ]
        elif isinstance(fields, bytes):
            fields = fields.decode()
            fields = [fields, ]

        # Build query here
        return f'SELECT {", ".join(fields)} FROM "{self.db_name}"."autogen"."{topic_name}" WHERE {timespan}'

    async def select_time_series(self, topic_name, fields, start, end, is_window=False, index=None):
        """Select a time series for a set of topics in a single subsystem"""
        query = self.build_time_range_query(topic_name, fields, start, end, is_window, index)
        # Do query
        ret = await self._do_query(query)
        if not isinstance(ret, pd.DataFrame) and not ret:
            # aioinflux returns an empty dict for an empty query
            ret = pd.DataFrame()
        return ret

    async def select_top_n(self, topic_name, fields, num):
        """Select the most recent N samples from a set of topics in a single subsystem.
           This method does not guarantee returned sorting direction rows.
        """

        # The "GROUP BY" is necessary to return the tags
        limit = f"GROUP BY * ORDER BY DESC LIMIT {num}"

        if isinstance(fields, str):
            fields = [fields, ]
        elif isinstance(fields, bytes):
            fields = fields.decode()
            fields = [fields, ]

        # Build query here
        query = f'SELECT {", ".join(fields)} FROM "{self.db_name}"."autogen"."{topic_name}" {limit}'

        # Do query
        ret = await self._do_query(query)
        if not isinstance(ret, pd.DataFrame) and not ret:
            # aioinflux returns an empty dict for an empty query
            ret = pd.DataFrame()
        return ret

    def _make_fields(self, fields, base_fields):
        ret = {}
        n = None
        for bfield in base_fields:
            for field in fields:
                if field.startswith(bfield) and field[len(bfield):].isdigit():  # Check prefix is complete
                    ret.setdefault(bfield, []).append(field)
            if n is None:
                n = len(ret[bfield])
            if n != len(ret[bfield]):
                raise ValueError(f'Field lengths do not agree for {bfield}: {n} vs. {len(ret[bfield])}')

            def sorter(prefix, val):
                return int(val[len(prefix):])

            part = partial(sorter, bfield)
            ret[bfield].sort(key=part)
        return ret, n

    async def select_packed_time_series(self, topic_name, base_fields, start, end,
                                        is_window=False, index=None, ref_timestamp_col="cRIO_timestamp"):
        """Select fields that are time samples and unpack them into a dataframe"""
        fields = await self.get_fields(topic_name)
        if isinstance(base_fields, str):
            base_fields = [base_fields, ]
        elif isinstance(base_fields, bytes):
            base_fields = base_fields.decode()
            base_fields = [base_fields, ]
        qfields, els = self._make_fields(fields, base_fields)
        field_list = []
        for k in qfields:
            field_list += qfields[k]
        result = await self.select_time_series(topic_name, field_list+[ref_timestamp_col, ],
                                               start, end, is_window=is_window, index=index)
        times = []
        timestamps = []
        vals = {}
        step = 1./els
        for tstamp, row in result.iterrows():  # for large numbers of columns itertuples doesn't work
            t = getattr(row, ref_timestamp_col)
            for i in range(els):
                times.append(t + i*step)
                # We need to convert to something bokeh knows about.
                timestamps.append((Time(t, format='unix', scale=self.internal_scale) +
                                   TimeDelta(i*step, format='sec')).datetime64)
                for k in qfields:
                    fld = f'{k}{i}'
                    if fld not in qfields[k]:
                        raise ValueError(f'{fld} not in field list')
                    vals.setdefault(k, []).append(getattr(row, fld))
        vals.update({'times': times})
        return pd.DataFrame(vals, index=timestamps)


def resample(df1, df2, sort_type='time'):
    df = df1.append(df2, sort=False)  # Sort in this context does not sort the data
    df = df.sort_index()
    return df.interpolate(type=sort_type)
