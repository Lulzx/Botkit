import asyncio
from typing import Coroutine, Dict, Iterable, List, Optional

from haps import Inject
from haps.config import Configuration

from botkit.builtin_services.options.base import IOptionStore
from ._module import Module
from .hmr import HotModuleReloadWorker
from .module_activator import ModuleActivator
from .module_status import ModuleStatus
from botkit.core.services import service
from botkit.utils.botkit_logging.setup import create_logger

DISABLED_MODULES = [
    "GameModule",
    "FunctionsBasedModule",
    "ReceiverModule",
    # belong together
    "IncomingMessagesModule",
    "ReplyModule",
    # end
    "NotionCollectorModule",
]


@service
class ModuleLoader:
    options: IOptionStore = Inject()
    activator: ModuleActivator = Inject()
    _hmr_worker: HotModuleReloadWorker = Inject()

    def __init__(self) -> None:
        self.log = create_logger()

        discovered_modules: List[Module] = Configuration().get_var("modules")
        self.log.debug(f"{len(discovered_modules)} modules discovered.")

        self.__module_statuses: Dict[Module, ModuleStatus] = {
            m: ModuleStatus.disabled if m.get_name() in DISABLED_MODULES else ModuleStatus.inactive
            for m in discovered_modules
        }

    @property
    def modules(self) -> Iterable[Module]:
        return self.__module_statuses.keys()

    @property
    def active_modules(self) -> Iterable[Module]:
        return (m for m, s in self.__module_statuses.items() if s == ModuleStatus.active)

    def add_module_without_activation(self, module: Module) -> None:
        self.__module_statuses[module] = ModuleStatus.inactive

    def get_module_by_name(self, name: str) -> Optional[Module]:
        return next((m for m in self.modules if m.get_name() == name), None)

    async def activate_enabled_modules(self) -> None:
        tasks: List[Coroutine] = []
        for n, module in enumerate(self.modules):
            module.index = n + 1
            tasks.append(self.try_activate_module(module))

        await asyncio.gather(*tasks)

        self._hmr_worker.start(self.modules)

    async def try_activate_module(self, module: Module) -> None:
        if module not in self.__module_statuses:
            self.add_module_without_activation(module)

        try:
            if self.get_module_status(module) == ModuleStatus.disabled:
                self.log.debug(f"{module.get_name()} is disabled.")
                module.route_collection = []
                return
            if self.get_module_status(module) == ModuleStatus.active:
                raise ValueError(
                    f"Nothing to do as the module '{module.get_name()}' is already active."
                )

            result: ModuleStatus = await self.activator.activate_module_async(module)
            self.__module_statuses[module] = result
            # TODO: maybe add a log message in which view_state the module now is (especially when failed)
        except:
            self.log.exception(f"Could not load {module.get_name()}.")

    def get_module_status(self, module: Module) -> ModuleStatus:
        return self.__module_statuses[module]
