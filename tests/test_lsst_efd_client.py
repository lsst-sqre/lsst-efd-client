#!/usr/bin/env python

"""Tests for `lsst_efd_client` package."""

import numpy
import pandas as pd
import pytest
from astropy.time import Time, TimeDelta
from aioinflux import InfluxDBClient
import pathlib

from lsst_efd_client import NotebookAuth, EfdClient, resample

PATH = pathlib.Path(__file__).parent.absolute()


@pytest.fixture
def auth_creds():
    """Sample pytest fixture to construct credentials to run tests on.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    return NotebookAuth().get_auth('test_efd')


@pytest.fixture
def auth_client():
    """Sample pytest fixture to construct an auth helper to run tests on.
    """
    return NotebookAuth()


@pytest.fixture
@pytest.mark.vcr
async def efd_client():
    df = pd.read_hdf(PATH/'efd_test.hdf')
    async with InfluxDBClient(db='client_test', mode='async', output='dataframe') as client:
        await client.create_database()
        await client.write(df, measurement='lsst.sal.fooSubSys.test')
        efd_client = EfdClient('test_efd', db_name='client_test', client=client)
        yield efd_client
        await client.drop_database()


@pytest.fixture
def expected_strs():
    expected = []
    with open(PATH/'expected.txt', 'r') as fh:
        for line in fh.readlines():
            expected.append(line)
    return expected


@pytest.fixture
def test_df():
    return pd.read_hdf(PATH/'efd_test.hdf')


@pytest.fixture
def start_stop():
    time = Time('2020-01-28T23:07:19.00', format='isot', scale='tai')
    return (time, time + TimeDelta(600, format='sec'))


def test_bad_endpoint():
    with pytest.raises(IOError):
        NotebookAuth(service_endpoint="https://no.path.here.net.gov")


@pytest.mark.vcr
def test_auth_host(auth_creds):
    assert auth_creds[0] == 'foo.bar.baz.net'


@pytest.mark.vcr
def test_auth_user(auth_creds):
    assert auth_creds[1] == 'foo'


@pytest.mark.vcr
def test_auth_password(auth_creds):
    assert auth_creds[2] == 'bar'


@pytest.mark.vcr
def test_auth_list(auth_client):
    # Make sure there is at least one set of credentials
    # other than the test one used here
    assert len(auth_client.list_auth()) > 1


@pytest.mark.vcr
def test_efd_names(auth_client):
    # Don't assume same order in case we change
    # the backend to something that doesn't
    # guarantee that
    for name in EfdClient.list_efd_names():
        assert name in auth_client.list_auth()


@pytest.mark.vcr
def test_build_query(efd_client, start_stop, expected_strs):
    # Check passing a single field works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', 'foo',
                                             start_stop[0], start_stop[1])
    assert qstr == expected_strs[0].strip()
    # Check passing a list of fields works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], start_stop[1])
    assert qstr == expected_strs[1].strip()


@pytest.mark.vcr
def test_build_query_delta(efd_client, start_stop, expected_strs):
    tdelta = TimeDelta(250, format='sec')
    # Check passing a time delta works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], tdelta)
    assert qstr == expected_strs[2].strip()
    # Check passing a time delta as a window works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], tdelta, is_window=True)
    assert qstr == expected_strs[3].strip()


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_topics(efd_client):
    topics = await efd_client.get_topics()
    assert len(topics) == 1
    assert topics[0] == 'lsst.sal.fooSubSys.test'


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fields(efd_client, test_df):
    columns = await efd_client.get_fields('lsst.sal.fooSubSys.test')
    for c in test_df.columns:
        assert c in columns


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_time_series(efd_client, start_stop):
    df = await efd_client.select_time_series('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], start_stop[1])
    assert len(df) == 600
    for c in ['foo', 'bar']:
        assert c in df.columns


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_top_n(efd_client, start_stop):
    df = await efd_client.select_top_n('lsst.sal.fooSubSys.test', ['foo', 'bar'], 10)
    assert len(df) == 10
    for c in ['foo', 'bar']:
        assert c in df.columns


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_packed_time_series(efd_client, start_stop):
    df_exp = pd.read_hdf(PATH/'packed_data.hdf', key='test_data')
    df = await efd_client.select_packed_time_series('lsst.sal.fooSubSys.test', ['ham', 'egg'],
                                                    start_stop[0], start_stop[1])
    assert numpy.all((df.index[1:] - df.index[:-1]).total_seconds() > 0)
    assert numpy.all(df == df_exp)
    assert numpy.all(df.index == df_exp.index)
    assert numpy.all(df['ham'] == df_exp['ham'])
    assert numpy.all(df['egg'] == df_exp['egg'])
    assert numpy.all(df['times'] == df_exp['times'])
    for c in ['ham', 'egg']:
        assert c in df.columns


def test_resample(test_df):
    df_copy = test_df.copy()
    df_copy.set_index(df_copy['tstamp'] + pd.Timedelta(0.5, unit='s'), inplace=True)
    df_out = resample(test_df, df_copy)
    assert len(df_out) == 2*len(test_df)
