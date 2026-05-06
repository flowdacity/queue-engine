# -*- coding: utf-8 -*-
# Copyright (c) 2025 Flowdacity Development Team. See LICENSE.txt for details.

import os
from collections.abc import Mapping

from fq.exceptions import BadArgumentException, FQException
from fq.utils import (
    convert_to_str,
    deserialize_payload,
    generate_epoch,
    is_valid_identifier,
    is_valid_interval,
    is_valid_requeue_limit,
    serialize_payload,
)

LUA_SCRIPT_NAMES = ("enqueue", "dequeue", "finish", "interval", "requeue", "metrics")
REDIS_CONN_TYPES = {"tcp_sock", "unix_sock"}

INVALID_INTERVAL = "`interval` has an invalid value."
INVALID_JOB_ID = "`job_id` has an invalid value."
INVALID_QUEUE_ID = "`queue_id` has an invalid value."
INVALID_QUEUE_TYPE = "`queue_type` has an invalid value."
INVALID_REQUEUE_LIMIT = "`requeue_limit` has an invalid value."


def normalize_config(config):
    normalized = _normalize_config_sections(config)
    _require_config_sections(normalized)

    redis_config = normalized["redis"]
    fq_config = normalized["fq"]

    _validate_redis_config(redis_config)
    _validate_fq_config(fq_config)
    _validate_connection_config(redis_config)
    _validate_optional_redis_config(redis_config)

    return normalized


def _normalize_config_sections(config):
    if not isinstance(config, Mapping):
        raise FQException("Config must be a mapping with redis and fq sections")

    normalized = {}
    for section_name, section_values in config.items():
        if not isinstance(section_values, Mapping):
            raise FQException("Config section '%s' must be a mapping" % section_name)

        normalized[str(section_name)] = {
            str(option): value for option, value in section_values.items()
        }

    return normalized


def _require_config_sections(config):
    if "redis" not in config or "fq" not in config:
        raise FQException("Config missing required sections: redis, fq")


def _require_config_value(config, section_name, option_name):
    if option_name not in config:
        raise FQException("Missing config: %s.%s" % (section_name, option_name))

    return config[option_name]


def _is_non_empty_string(value):
    return isinstance(value, str) and bool(value)


def _is_int_not_bool(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_redis_config(redis_config):
    key_prefix = _require_config_value(redis_config, "redis", "key_prefix")
    if not _is_non_empty_string(key_prefix):
        raise FQException("Invalid config: redis.key_prefix must be a non-empty string")

    conn_type = _require_config_value(redis_config, "redis", "conn_type")
    if conn_type not in REDIS_CONN_TYPES:
        raise FQException(
            "Invalid config: redis.conn_type must be 'tcp_sock' or 'unix_sock'"
        )

    db = _require_config_value(redis_config, "redis", "db")
    if not _is_int_not_bool(db):
        raise FQException("Invalid config: redis.db must be an integer")


def _validate_fq_config(fq_config):
    for option_name in ("job_expire_interval", "job_requeue_interval"):
        value = _require_config_value(fq_config, "fq", option_name)
        if not is_valid_interval(value):
            raise FQException(
                "Invalid config: fq.%s must be a positive integer" % option_name
            )

    default_requeue_limit = _require_config_value(
        fq_config, "fq", "default_job_requeue_limit"
    )
    if not is_valid_requeue_limit(default_requeue_limit):
        raise FQException(
            "Invalid config: fq.default_job_requeue_limit must be an integer >= -1"
        )


def _validate_connection_config(redis_config):
    if redis_config["conn_type"] == "unix_sock":
        _validate_unix_socket_config(redis_config)
        return

    _validate_tcp_socket_config(redis_config)


def _validate_unix_socket_config(redis_config):
    unix_socket_path = _require_config_value(
        redis_config, "redis", "unix_socket_path"
    )
    if not _is_non_empty_string(unix_socket_path):
        raise FQException(
            "Invalid config: redis.unix_socket_path must be a non-empty string"
        )


def _validate_tcp_socket_config(redis_config):
    host = _require_config_value(redis_config, "redis", "host")
    if not _is_non_empty_string(host):
        raise FQException("Invalid config: redis.host must be a non-empty string")

    port = _require_config_value(redis_config, "redis", "port")
    if not _is_int_not_bool(port):
        raise FQException("Invalid config: redis.port must be an integer")

    if "clustered" in redis_config and not isinstance(redis_config["clustered"], bool):
        raise FQException("Invalid config: redis.clustered must be a boolean")


def _validate_optional_redis_config(redis_config):
    if "password" in redis_config and redis_config["password"] is not None:
        if not isinstance(redis_config["password"], str):
            raise FQException("Invalid config: redis.password must be a string")


def _validate_identifier(identifier, message):
    if not is_valid_identifier(identifier):
        raise BadArgumentException(message)


def load_lua_scripts(instance, redis_client):
    lua_script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "scripts", "lua"
    )

    for script_name in LUA_SCRIPT_NAMES:
        with open(
            os.path.join(lua_script_path, "%s.lua" % script_name),
            "r",
            encoding="utf-8",
        ) as script_file:
            script = script_file.read()
            setattr(instance, "_lua_%s_script" % script_name, script)
            setattr(
                instance,
                "_lua_%s" % script_name,
                redis_client.register_script(script),
            )


def validate_enqueue_arguments(
    payload,
    interval,
    job_id,
    queue_id,
    queue_type,
    requeue_limit,
    default_requeue_limit,
):
    if not is_valid_interval(interval):
        raise BadArgumentException(INVALID_INTERVAL)

    _validate_identifier(job_id, INVALID_JOB_ID)
    _validate_identifier(queue_id, INVALID_QUEUE_ID)
    _validate_identifier(queue_type, INVALID_QUEUE_TYPE)

    if requeue_limit is None:
        requeue_limit = default_requeue_limit

    if not is_valid_requeue_limit(requeue_limit):
        raise BadArgumentException(INVALID_REQUEUE_LIMIT)

    try:
        serialized_payload = serialize_payload(payload)
    except TypeError:
        raise BadArgumentException("can not serialize.")

    return serialized_payload, requeue_limit


def validate_dequeue_arguments(queue_type):
    _validate_identifier(queue_type, INVALID_QUEUE_TYPE)


def validate_finish_arguments(job_id, queue_id, queue_type):
    _validate_identifier(job_id, INVALID_JOB_ID)
    _validate_identifier(queue_id, INVALID_QUEUE_ID)
    _validate_identifier(queue_type, INVALID_QUEUE_TYPE)


def validate_interval_arguments(interval, queue_id, queue_type):
    if not is_valid_interval(interval):
        raise BadArgumentException(INVALID_INTERVAL)

    _validate_identifier(queue_id, INVALID_QUEUE_ID)
    _validate_identifier(queue_type, INVALID_QUEUE_TYPE)


def validate_metrics_arguments(queue_type, queue_id):
    if queue_id is not None and not is_valid_identifier(queue_id):
        raise BadArgumentException(INVALID_QUEUE_ID)

    if queue_type is not None and not is_valid_identifier(queue_type):
        raise BadArgumentException(INVALID_QUEUE_TYPE)


def validate_clear_queue_arguments(queue_type, queue_id):
    if queue_id is None or not is_valid_identifier(queue_id):
        raise BadArgumentException(INVALID_QUEUE_ID)

    if queue_type is None or not is_valid_identifier(queue_type):
        raise BadArgumentException(INVALID_QUEUE_TYPE)


def validate_get_queue_length_arguments(queue_type, queue_id):
    _validate_identifier(queue_type, INVALID_QUEUE_TYPE)
    _validate_identifier(queue_id, INVALID_QUEUE_ID)


def decode_redis_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def format_dequeue_response(dequeue_response):
    if len(dequeue_response) < 4:
        return {"status": "failure"}

    queue_id, job_id, payload, requeues_remaining = dequeue_response

    if payload is None:
        return {"status": "failure"}

    payload = deserialize_payload(payload)

    return {
        "status": "success",
        "queue_id": decode_redis_value(queue_id),
        "job_id": decode_redis_value(job_id),
        "payload": payload,
        "requeues_remaining": int(requeues_remaining),
    }


def format_metrics_counts(enqueue_details, dequeue_details):
    enqueue_counts = {}
    dequeue_counts = {}
    for i in range(0, len(enqueue_details), 2):
        enqueue_counts[str(decode_redis_value(enqueue_details[i]))] = int(
            enqueue_details[i + 1] or 0
        )
        dequeue_counts[str(decode_redis_value(dequeue_details[i]))] = int(
            dequeue_details[i + 1] or 0
        )
    return enqueue_counts, dequeue_counts


def format_queue_types(active_queue_types, ready_queue_types):
    return convert_to_str(active_queue_types | ready_queue_types)


def format_queue_ids(ready_queues, active_queues):
    active_queues = [decode_redis_value(i).split(":")[0] for i in active_queues]
    all_queue_set = set(ready_queues) | set(active_queues)
    return convert_to_str(all_queue_set)


def enqueue_script_args(
    key_prefix,
    queue_type,
    queue_id,
    job_id,
    serialized_payload,
    interval,
    requeue_limit,
):
    timestamp = str(generate_epoch())
    keys = [key_prefix, queue_type]
    args = [
        timestamp,
        queue_id,
        job_id,
        serialized_payload,
        interval,
        requeue_limit,
    ]
    return keys, args
