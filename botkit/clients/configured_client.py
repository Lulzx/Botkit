from abc import abstractmethod
from sqlite3 import OperationalError

from decouple import config
from pyrogram import Client
from pyrogram.types import User

from botkit.clients.client_config import ClientConfig
from botkit.utils.botkit_logging.setup import create_logger

log = create_logger("configured_client")


def create_session_name_from_token(bot_token: str) -> str:
    res = bot_token.split(":")[0]
    return res


class ConfiguredClient(Client):
    def __init__(self, **kwargs) -> None:
        session_name = self.config.session_string or self.config.session_path
        merged_args = dict(
            api_id=config("API_ID"),
            api_hash=config("API_HASH"),
            bot_token=self.config.bot_token if self.config else None,
            phone_number=self.config.phone_number if self.config else None,
        )
        merged_args.update(kwargs)

        if (
            not self.config.session_string
            and session_name
            and (bot_token := merged_args.get("bot_token", None))
        ):
            # noinspection PyUnboundLocalVariable
            session_name = create_session_name_from_token(bot_token)

        log.warning(session_name)
        super().__init__(session_name, **merged_args)
        self._me = None

    @property
    @abstractmethod
    def config(self) -> ClientConfig:
        # noinspection PydanticTypeChecker
        return None

    async def get_me(self) -> User:
        if self._me is not None:
            return self._me
        self._me = await super().get_me()
        return self._me
