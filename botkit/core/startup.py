import asyncio
import logging
import signal
from abc import abstractmethod
from asyncio.events import AbstractEventLoop

from haps import Inject, base
from haps.application import Application
from pyrogram import Client as PyrogramClient

from botkit.core.modules import ModuleLoader
from botkit.settings import botkit_settings
from botkit.utils.botkit_logging.setup import create_logger

try:
    # noinspection PyUnresolvedReferences
    from telethon import TelegramClient as TelethonClient
except:
    TelethonClient = None

from typing import List, Union

from botkit.core.modules._module import Module
from botkit.tghelpers.names import user_or_display_name
from abc import ABC

Client = Union[PyrogramClient, TelethonClient]


@base
class Startup(Application, ABC):
    module_loader: ModuleLoader = Inject()

    def __init__(self, clients: List[Client]):
        if not clients:
            raise ValueError("Must pass at least one client for initialization.")
        self.clients = clients

        self.log = create_logger("startup")

    @abstractmethod
    async def run_startup_tasks(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass

    async def _start_clients(self):
        self.log.debug("Starting clients...")
        start_tasks = (self.__start_client(c) for c in self.clients)
        await asyncio.gather(*start_tasks)

    async def __start_client(self, client):
        session_path = (
            client.session_name if hasattr(client, "session_name") else client.session.filename
        )

        self.log.debug(f"Starting session " f"{session_path}...")
        await client.start()
        me = await client.get_me()
        self.log.info(f"Started {user_or_display_name(me)} as {client.__class__.__name__}.")

    def run(self, loop: AbstractEventLoop = None) -> None:
        self.log.debug("Initializing...")
        loop = loop or asyncio.get_event_loop()

        try:
            signals = [signal.SIGTERM, signal.SIGINT]
            for s in signals:
                loop.add_signal_handler(s, lambda s=s: asyncio.create_task(self._shutdown(loop)))
        except NotImplementedError:
            pass  # Windows does not implement signals

        loop.run_until_complete(self._start_async())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self._shutdown(loop))
            logging.info("Graceful shutdown.")
            loop.close()

    def get_extra_modules(self) -> List[Module]:
        return []

    async def _start_async(self):
        await self._start_clients()
        for m in self.get_extra_modules() or []:
            self.module_loader.add_module_without_activation(m)
        await self.module_loader.activate_enabled_modules()
        await self.run_startup_tasks()
        self.log.info("Ready.")

    async def _shutdown(self, loop: AbstractEventLoop):
        self.log.info("Shutting down...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        self.log.info(f"Cancelling {len(tasks)} running or outstanding tasks")
        await asyncio.gather(*tasks)
        await self.on_shutdown()
        self.log.info("Graceful shutdown complete. Goodbye")
        loop.stop()
