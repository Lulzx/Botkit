from abc import ABC
from typing import (
    Generic,
    Union,
    overload,
)

from pyrogram.types import ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove

from botkit.abstractions import IRegisterable
from botkit.builders.menubuilder import MenuBuilder
from botkit.builders.metabuilder import MetaBuilder
from botkit.views.rendered_messages import RenderedMessage
from botkit.views.types import TViewState


class ModelViewBase(Generic[TViewState], ABC):
    def __init__(self, state: TViewState):
        self.state = state


class InlineResultViewBase(ModelViewBase, IRegisterable, Generic[TViewState], ABC):
    def assemble_metadata(self, meta: MetaBuilder):
        pass

    def render(self) -> RenderedMessage:
        meta_builder = MetaBuilder()
        self.assemble_metadata(meta_builder)
        return RenderedMessage(title=meta_builder.title, description=meta_builder.description)


class RenderMarkupBase:  # not an interface as the methods need to exist
    @overload
    def render_markup(self, menu: MenuBuilder):
        pass

    @overload
    def render_markup(self,) -> Union[ReplyKeyboardMarkup, ForceReply, ReplyKeyboardRemove]:
        pass

    def render_markup(self, *args):
        pass
