# -*- coding: utf-8 -*-
# Copyright (c) 2025 Flowdacity Development Team. See LICENSE.txt for details.

from dataclasses import dataclass


@dataclass(frozen=True)
class RedisKeys:
    key_prefix: str

    @property
    def active_queue_types(self) -> str:
        return "%s:active:queue_type" % self.key_prefix

    @property
    def ready_queue_types(self) -> str:
        return "%s:ready:queue_type" % self.key_prefix

    @property
    def interval_hash(self) -> str:
        return "%s:interval" % self.key_prefix

    @property
    def payload_hash(self) -> str:
        return "%s:payload" % self.key_prefix

    @property
    def deep_status(self) -> str:
        return "fq:deep_status:%s" % self.key_prefix

    def ready_queue_set(self, queue_type: str) -> str:
        return "%s:%s" % (self.key_prefix, queue_type)

    def active_queue_set(self, queue_type: str) -> str:
        return "%s:%s:active" % (self.key_prefix, queue_type)

    def job_queue(self, queue_type: str, queue_id: str) -> str:
        return "%s:%s:%s" % (self.key_prefix, queue_type, queue_id)

    def interval_member(self, queue_type: str, queue_id: str) -> str:
        return "%s:%s" % (queue_type, queue_id)

    def payload_member(self, queue_type: str, queue_id: str, job_id: str) -> str:
        return "%s:%s:%s" % (queue_type, queue_id, job_id)
