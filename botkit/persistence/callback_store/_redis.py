import logging
from pprint import pprint

from botkit.settings import botkit_settings
from ...utils.botkit_logging.setup import create_logger

from haps import Container, SINGLETON_SCOPE, egg, scope
from datetime import datetime, timedelta
from haps import base
from typing import Dict, List, Literal, Optional, Union
from uuid import UUID

from redis import Redis
from redis_collections import Dict as RedisDict, LRUDict

from ._base import (
    ICallbackStore,
    generate_id,
)
from ._base import CallbackActionContext

log = create_logger("redis_callbacks")

# noinspection PyUnresolvedReferences
base.classes.add(Redis)


class RedisClientUnavailableException(Exception):
    pass


@egg("redis")
@scope(SINGLETON_SCOPE)
def create_redis_callback_manager() -> ICallbackStore:
    try:
        redis = Container().get_object(Redis)
    except Exception as e:
        raise RedisClientUnavailableException(
            "If `redis` is chosen as the qualifier for the botkit callback manager, "
            "you must provide an instantiated `Redis` client to the dependency "
            "injection. Refer to the `callback_manager_qualifier` setting documentation."
        ) from e
    redis_cbm = RedisCallbackStore(redis, "callbacks", maxsize=10)
    redis_cbm.remove_outdated(botkit_settings.callbacks_ttl_days)
    return redis_cbm


class RedisCallbackStore(ICallbackStore):
    """
    # TODO: Try use json instead of pickled dicts? https://github.com/honzajavorek/redis-collections/issues/122
    # TODO: Force pydantic models?
    """

    def __init__(
        self,
        redis_client: Redis,
        key: str = "callbacks",
        storage_type: Literal["lru", "normal"] = "normal",
        maxsize: int = 2000,
    ):
        """

        :param redis_client:
        :type redis_client:
        :param key:
        :type key:
        :param storage_type:
        :type storage_type:
        :param maxsize: Ignored if storage_type is "normal".
        :type maxsize:
        """
        # TODO: Add documentation that LRU should be used in production
        if storage_type == "lru":
            self.callbacks: LRUDict[str, Dict] = LRUDict(
                maxsize=maxsize, redis=redis_client, key=key + "_lru_dict"
            )
        elif storage_type == "normal":
            self.callbacks: RedisDict[str, Dict] = RedisDict(
                redis=redis_client, key=key + "_normal_dict"
            )

        self.fallback_memory_callbacks = dict()

    def create_callback(self, context: CallbackActionContext) -> str:
        id_ = generate_id()
        serialized = context.dict()

        try:
            self.callbacks[id_] = serialized
        except TypeError as e:
            log.error(
                f"{e} -- "
                "Callback context could not be serialized. Using in-memory store instead, so this"
                "callback will be lost on system restart."
            )
            self.fallback_memory_callbacks = serialized
        return id_

    def lookup_callback(self, id_: Union[str, UUID]) -> Optional[CallbackActionContext]:
        id_ = str(id_).strip()
        context: Optional[Dict] = self.callbacks.get(id_)
        if context is None:
            context = self.fallback_memory_callbacks.get(id_)
            if context is None:
                return None
        return CallbackActionContext(**context)

    def clear(self):
        self.callbacks.clear()

    def force_sync(self):
        self.callbacks.sync()

    def remove_outdated(self, days: int = 7):
        now = datetime.utcnow()
        to_remove: List[str] = []

        # pipe = self.redis if pipe is None else pipe
        # if isinstance(pipe, Pipeline):
        #     pipe.hgetall(self.key)
        #     items = pipe.execute()[-1].items()
        # else:
        #     items = self.redis.hgetall(self.key).items()
        #
        # return {self._unpickle_key(k): self._unpickle(v) for k, v in items}

        try:
            for k, v in self.callbacks.items():
                if "created" not in v:
                    print("created not in v")
                    to_remove.append(k)
                elif v.get("created") + timedelta(days=7) <= now:
                    to_remove.append(k)

            for i in to_remove:
                self.callbacks.pop(i)

            if (num_removed := len(to_remove)) > 0:
                log.info(f"Dropped {num_removed} outdated callbacks.")
        except Exception as e:
            log.error(e)
            log.info("Recreating callbacks...")
            self.callbacks.clear()
