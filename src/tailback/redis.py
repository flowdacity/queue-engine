# -*- coding: utf-8 -*-
# Copyright (c) 2025 Flowdacity Development Team. See LICENSE.txt for details.

from typing import Any, cast

from redis import Redis as SyncRedis
from redis import RedisCluster as SyncRedisCluster
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.cluster import ClusterNode as AsyncClusterNode
from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster

from tailback.config import RedisConfig
from tailback.exceptions import TailbackException


def create_async_redis_client(
    redis_config: RedisConfig,
) -> AsyncRedis | AsyncRedisCluster:
    if redis_config.conn_type == "unix_sock":
        return AsyncRedis(
            db=redis_config.db,
            unix_socket_path=redis_config.unix_socket_path,
            password=redis_config.password,
        )

    if redis_config.conn_type == "tcp_sock":
        host = cast(str, redis_config.host)
        port = int(cast(int, redis_config.port))
        if redis_config.clustered:
            startup_nodes = [
                AsyncClusterNode(host, port),
            ]
            return AsyncRedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=False,
                password=redis_config.password,
                socket_timeout=5,
            )

        return AsyncRedis(
            db=redis_config.db,
            host=host,
            port=port,
            password=redis_config.password,
        )

    raise TailbackException("Unknown redis conn_type: %s" % redis_config.conn_type)


def create_sync_redis_client(redis_config: RedisConfig) -> SyncRedis | SyncRedisCluster:
    if redis_config.conn_type == "unix_sock":
        return SyncRedis(
            db=redis_config.db,
            unix_socket_path=redis_config.unix_socket_path,
            password=redis_config.password,
        )

    if redis_config.conn_type == "tcp_sock":
        host = cast(str, redis_config.host)
        port = int(cast(int, redis_config.port))
        if redis_config.clustered:
            return SyncRedisCluster(
                host=host,
                port=port,
                decode_responses=False,
                password=redis_config.password,
                socket_timeout=5,
            )

        return SyncRedis(
            db=redis_config.db,
            host=host,
            port=port,
            password=redis_config.password,
        )

    raise TailbackException("Unknown redis conn_type: %s" % redis_config.conn_type)


async def validate_async_redis_connection(redis_client: Any) -> None:
    if redis_client is None:
        raise TailbackException("Redis client is not initialized")

    ping = getattr(redis_client, "ping", None)
    if not callable(ping):
        return

    try:
        result = await ping()
    except Exception as exc:
        raise TailbackException("Failed to connect to Redis: %s" % exc) from exc

    if result is False:
        raise TailbackException("Failed to connect to Redis: ping returned False")


def validate_sync_redis_connection(redis_client: Any) -> None:
    if redis_client is None:
        raise TailbackException("Redis client is not initialized")

    ping = getattr(redis_client, "ping", None)
    if not callable(ping):
        return

    try:
        result = ping()
    except Exception as exc:
        raise TailbackException("Failed to connect to Redis: %s" % exc) from exc

    if result is False:
        raise TailbackException("Failed to connect to Redis: ping returned False")
