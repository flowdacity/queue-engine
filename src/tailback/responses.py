# -*- coding: utf-8 -*-
# Copyright (c) 2025 Flowdacity Development Team. See LICENSE.txt for details.

from collections.abc import Iterable, Sequence
from typing import Any

from tailback.utils import convert_to_str, deserialize_payload

RedisValue = str | bytes


def decode_redis_value(value: RedisValue) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def format_dequeue_response(dequeue_response: Sequence[Any]) -> dict[str, Any]:
    if len(dequeue_response) < 4:
        return {"status": "failure"}

    queue_id, job_id, payload, requeues_remaining = dequeue_response

    if payload is None:
        return {"status": "failure"}

    return {
        "status": "success",
        "queue_id": decode_redis_value(queue_id),
        "job_id": decode_redis_value(job_id),
        "payload": deserialize_payload(payload),
        "requeues_remaining": int(requeues_remaining),
    }


def format_metrics_counts(
    enqueue_details: Sequence[Any],
    dequeue_details: Sequence[Any],
) -> tuple[dict[str, int], dict[str, int]]:
    enqueue_counts: dict[str, int] = {}
    dequeue_counts: dict[str, int] = {}
    for i in range(0, len(enqueue_details), 2):
        enqueue_counts[str(decode_redis_value(enqueue_details[i]))] = int(
            enqueue_details[i + 1] or 0
        )
        dequeue_counts[str(decode_redis_value(dequeue_details[i]))] = int(
            dequeue_details[i + 1] or 0
        )
    return enqueue_counts, dequeue_counts


def format_queue_types(
    active_queue_types: Iterable[RedisValue],
    ready_queue_types: Iterable[RedisValue],
) -> list[str]:
    return convert_to_str(set(active_queue_types) | set(ready_queue_types))


def format_queue_ids(
    ready_queues: Iterable[RedisValue],
    active_queues: Iterable[RedisValue],
) -> list[str]:
    ready_queue_ids = {decode_redis_value(queue) for queue in ready_queues}
    active_queue_ids = {
        decode_redis_value(queue).split(":")[0] for queue in active_queues
    }
    return convert_to_str(ready_queue_ids | active_queue_ids)
