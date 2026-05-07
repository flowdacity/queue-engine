# -*- coding: utf-8 -*-
# Copyright (c) 2025 Flowdacity Development Team. See LICENSE.txt for details.

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from tailback.config import TailbackConfig
from tailback.exceptions import BadArgumentException
from tailback.keys import RedisKeys
from tailback.responses import (
    RedisValue,
    decode_redis_value,
    format_dequeue_response,
    format_metrics_counts,
    format_queue_ids,
    format_queue_types,
)
from tailback.utils import generate_epoch
from tailback.validators import (
    validate_clear_queue_arguments,
    validate_dequeue_arguments,
    validate_enqueue_arguments,
    validate_finish_arguments,
    validate_get_queue_length_arguments,
    validate_interval_arguments,
    validate_metrics_arguments,
)

RedisCall = tuple[list[str], list[Any]]
StatusResponse = dict[str, str]


@dataclass(frozen=True)
class ClearQueuePlan:
    primary_set: str
    job_queue: str
    payload_hash: str
    interval_hash: str
    interval_member: str
    queue_type: str
    queue_id: str

    def payload_member(self, job_id: str) -> str:
        return "%s:%s:%s" % (self.queue_type, self.queue_id, job_id)


class BaseTailback(object):
    """Shared non-I/O behavior for async and sync Tailback clients."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self._r: Any = None
        self._scripts: Any = None
        self.config: TailbackConfig = TailbackConfig.from_mapping(config)
        self._keys: RedisKeys = RedisKeys(self.config.queue.key_prefix)

        self._key_prefix: str = self.config.queue.key_prefix
        self._job_expire_interval: int = int(self.config.queue.job_expire_interval)
        self._default_job_requeue_limit: int = int(
            self.config.queue.default_job_requeue_limit
        )

    def redis_client(self) -> Any | None:
        return self._r

    def _current_timestamp(self) -> str:
        return str(generate_epoch())

    def _build_enqueue_call(
        self,
        payload: Any,
        interval: int,
        job_id: str,
        queue_id: str,
        queue_type: str,
        requeue_limit: int | None,
    ) -> RedisCall:
        enqueue_args = validate_enqueue_arguments(
            payload,
            interval,
            job_id,
            queue_id,
            queue_type,
            requeue_limit,
            self._default_job_requeue_limit,
        )
        keys = [self._key_prefix, queue_type]
        args = [
            self._current_timestamp(),
            queue_id,
            job_id,
            enqueue_args.serialized_payload,
            interval,
            enqueue_args.requeue_limit,
        ]
        return keys, args

    def _build_dequeue_call(self, queue_type: str) -> RedisCall:
        validate_dequeue_arguments(queue_type)
        return [self._key_prefix, queue_type], [
            self._current_timestamp(),
            self._job_expire_interval,
        ]

    def _build_finish_call(
        self,
        job_id: str,
        queue_id: str,
        queue_type: str,
    ) -> RedisCall:
        validate_finish_arguments(job_id, queue_id, queue_type)
        return [self._key_prefix, queue_type], [queue_id, job_id]

    def _build_interval_call(
        self,
        interval: int,
        queue_id: str,
        queue_type: str,
    ) -> RedisCall:
        validate_interval_arguments(interval, queue_id, queue_type)
        keys = [
            self._keys.interval_hash,
            self._keys.interval_member(queue_type, queue_id),
        ]
        return keys, [interval]

    def _build_requeue_call(self, queue_type: RedisValue, timestamp: str) -> RedisCall:
        queue_type = decode_redis_value(queue_type)
        return [self._key_prefix, queue_type], [timestamp]

    def _build_global_metrics_call(self) -> RedisCall:
        return [self._key_prefix], [self._current_timestamp()]

    def _build_queue_metrics_call(self, queue_type: str, queue_id: str) -> RedisCall:
        return [self._keys.job_queue(queue_type, queue_id)], [self._current_timestamp()]

    def _validate_metrics_call(
        self,
        queue_type: str | None,
        queue_id: str | None,
    ) -> None:
        validate_metrics_arguments(queue_type, queue_id)
        if not queue_type and queue_id:
            raise BadArgumentException(
                "`queue_id` should be accompanied by `queue_type`."
            )

    def _queue_type_metrics_keys(self, queue_type: str) -> tuple[str, str]:
        return (
            self._keys.ready_queue_set(queue_type),
            self._keys.active_queue_set(queue_type),
        )

    def _queue_length_key(self, queue_type: str, queue_id: str) -> str:
        validate_get_queue_length_arguments(queue_type, queue_id)
        return self._keys.job_queue(queue_type, queue_id)

    def _clear_queue_plan(
        self,
        queue_type: str | None,
        queue_id: str | None,
    ) -> ClearQueuePlan:
        validate_clear_queue_arguments(queue_type, queue_id)
        queue_type = cast(str, queue_type)
        queue_id = cast(str, queue_id)
        return ClearQueuePlan(
            primary_set=self._keys.ready_queue_set(queue_type),
            job_queue=self._keys.job_queue(queue_type, queue_id),
            payload_hash=self._keys.payload_hash,
            interval_hash=self._keys.interval_hash,
            interval_member=self._keys.interval_member(queue_type, queue_id),
            queue_type=queue_type,
            queue_id=queue_id,
        )

    def _finish_response(self, finish_response: int) -> StatusResponse:
        if finish_response == 0:
            return {"status": "failure"}
        return {"status": "success"}

    def _interval_response(self, interval_response: int) -> StatusResponse:
        if interval_response == 0:
            return {"status": "failure"}
        return {"status": "success"}

    def _dequeue_response(self, dequeue_response: Sequence[Any]) -> dict[str, Any]:
        return format_dequeue_response(dequeue_response)

    def _global_metrics_response(
        self,
        active_queue_types: Iterable[RedisValue],
        ready_queue_types: Iterable[RedisValue],
        enqueue_details: Sequence[Any],
        dequeue_details: Sequence[Any],
    ) -> dict[str, Any]:
        enqueue_counts, dequeue_counts = format_metrics_counts(
            enqueue_details,
            dequeue_details,
        )
        return {
            "status": "success",
            "queue_types": format_queue_types(active_queue_types, ready_queue_types),
            "enqueue_counts": enqueue_counts,
            "dequeue_counts": dequeue_counts,
        }

    def _queue_type_metrics_response(
        self,
        ready_queues: Iterable[RedisValue],
        active_queues: Iterable[RedisValue],
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "queue_ids": format_queue_ids(ready_queues, active_queues),
        }

    def _queue_metrics_response(
        self,
        queue_length: int | str | bytes,
        enqueue_details: Sequence[Any],
        dequeue_details: Sequence[Any],
    ) -> dict[str, Any]:
        enqueue_counts, dequeue_counts = format_metrics_counts(
            enqueue_details,
            dequeue_details,
        )
        return {
            "status": "success",
            "queue_length": int(queue_length),
            "enqueue_counts": enqueue_counts,
            "dequeue_counts": dequeue_counts,
        }

    def _decode_redis_value(self, value: RedisValue) -> str:
        return decode_redis_value(value)

    def _decode_requeue_job(self, job: RedisValue) -> tuple[str, str]:
        queue_id, job_id = decode_redis_value(job).split(":")
        return queue_id, job_id

    def _clear_queue_empty_response(self) -> StatusResponse:
        return {"status": "Failure", "message": "No queued calls found"}

    def _clear_queue_removed_response(self) -> StatusResponse:
        return {
            "status": "Success",
            "message": "Successfully removed all queued calls",
        }

    def _clear_queue_purged_response(self) -> StatusResponse:
        return {
            "status": "Success",
            "message": "Successfully removed all queued calls and purged related resources",
        }
