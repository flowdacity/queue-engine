# -*- coding: utf-8 -*-

from copy import deepcopy


TEST_CONFIG = {
    "fq": {
        "job_expire_interval": 5000,
        "job_requeue_interval": 5000,
        "default_job_requeue_limit": -1,
    },
    "redis": {
        "db": 0,
        "key_prefix": "test_fq",
        "conn_type": "tcp_sock",
        "unix_socket_path": "/tmp/redis.sock",
        "port": 6379,
        "host": "127.0.0.1",
        "clustered": False,
        "password": "",
    },
}


def build_test_config(**section_overrides):
    config = deepcopy(TEST_CONFIG)
    for section_name, overrides in section_overrides.items():
        config.setdefault(section_name, {})
        config[section_name].update(overrides)
    return config
