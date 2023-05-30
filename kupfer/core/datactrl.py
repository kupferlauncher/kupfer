""" DataController """
from __future__ import annotations

import itertools
import os
import sys
import typing as ty
from collections import defaultdict
from contextlib import suppress
from enum import IntEnum
from pathlib import Path

from gi.repository import GLib, GObject

from kupfer.obj import compose
from kupfer.obj.base import (
    Action,
    ActionGenerator,
    AnySource,
    KupferObject,
    Leaf,
    Source,
    TextSource,
)
from kupfer.obj.filesrc import DirectorySource, FileSource
from kupfer.support import pretty, scheduler
from kupfer.support.types import ExecInfo
from kupfer.ui.uievents import GUIEnvironmentContext

from . import commandexec, execfile, learn, pluginload, qfurl, search, settings
from .panes import (
    LeafPane,
    Pane,
    PrimaryActionPane,
    SearchContext,
    SecondaryObjectPane,
)
from .search import Rankable
from .sources import get_source_controller

DATA_SAVE_INTERVAL_S = 3660


# "Enums"
# Which pane
class PaneSel(IntEnum):
    SOURCE = 1
    ACTION = 2
    OBJECT = 3


# In two-pane or three-pane mode
class PaneMode(IntEnum):
    SOURCE_ACTION = 1
    SOURCE_ACTION_OBJECT = 2


# pylint: disable=too-many-public-methods
class DataController(GObject.GObject, pretty.OutputMixin):  # type:ignore
    """Sources <-> Actions controller.

    The data controller must be created before main program commences,
    so it can register itself at the scheduler correctly.
    """

    _instance: DataController | None = None

    @classmethod
    def instance(cls) -> DataController:
        """Get instance of DataController."""
        if cls._instance is None:
            cls._instance = DataController()

        return cls._instance

    __gtype_name__ = "DataController"

    def __init__(self):
        super().__init__()

        self._source_pane = LeafPane()
        self._source_pane.connect("new-source", self._on_new_source)
        self._object_pane = SecondaryObjectPane()
        self._object_pane.connect("new-source", self._on_new_source)
        self._action_pane = PrimaryActionPane()
        for pane, ctl in self._all_pane_ctl():
            ctl.connect("search-result", self._on_pane_search_result, pane)

        self._mode: PaneMode | None = None
        self._search_ids = itertools.count(1)
        self._latest_interaction = -1
        self._execution_context = commandexec.default_action_execution_context()
        self._execution_context.connect(
            "command-result", self._on_command_execution_result
        )
        self._execution_context.connect(
            "late-command-result", self._on_late_command_execution_result
        )

        self._save_data_timer = scheduler.Timer()

        sch = scheduler.get_scheduler()
        sch.connect("load", self._on_load)
        sch.connect("display", self._on_display)
        sch.connect("finish", self._on_finish)

    def _get_panectl(self, pane: PaneSel) -> Pane[KupferObject]:
        if pane == PaneSel.SOURCE:
            return self._source_pane
        if pane == PaneSel.ACTION:
            return self._action_pane
        if pane == PaneSel.OBJECT:
            return self._object_pane

        raise ValueError(f"invalid pane {pane}")

    def _all_pane_ctl(self) -> ty.Iterator[tuple[PaneSel, Pane[KupferObject]]]:
        yield PaneSel.SOURCE, self._source_pane
        yield PaneSel.ACTION, self._action_pane
        yield PaneSel.OBJECT, self._object_pane

    def _register_text_sources(
        self, plugin_id: str, srcs: ty.Iterable[TextSource]
    ) -> None:
        """Pass in text sources as @srcs

        we register text sources"""
        sctr = get_source_controller()
        sctr.add_text_sources(plugin_id, srcs)

    def _register_action_decorators(
        self, plugin_id: str, actions: list[Action]
    ) -> None:
        # Keep a mapping: Decorated Leaf Type -> List of actions
        decorate_types: defaultdict[ty.Any, list[Action]] = defaultdict(list)
        for action in actions:
            for appl_type in action.item_types():
                decorate_types[appl_type].append(action)

        if not decorate_types:
            return

        sctr = get_source_controller()
        sctr.add_action_decorators(plugin_id, decorate_types)

    def _register_content_decorators(
        self, plugin_id: str, contents: ty.Collection[ty.Type[Source]]
    ) -> None:
        """Register the sequence of classes @contents as
        potential content decorators. Classes not conforming to
        the decoration protocol (most importantly, ``.decorates_type()``)
        will be skipped."""
        # Keep a mapping:
        # Decorated Leaf Type -> Set of content decorator types
        decorate_item_types: defaultdict[
            ty.Type[Leaf], set[ty.Type[Source]]
        ] = defaultdict(set)

        for content in contents:
            with suppress(AttributeError):
                applies = content.decorates_type()  # type: ignore
                decorate_item_types[applies].add(content)

        if not decorate_item_types:
            return

        sctr = get_source_controller()
        sctr.add_content_decorators(plugin_id, decorate_item_types)

    def _register_action_generators(
        self, plugin_id: str, generators: ty.Iterable[ActionGenerator]
    ) -> None:
        sctr = get_source_controller()
        for generator in generators:
            sctr.add_action_generator(plugin_id, generator)

    def _on_load(self, _sched: ty.Any) -> None:
        """Begin Data Controller work when we get application 'load' signal.

        Load the data model from saved configuration and caches
        """
        setctl = settings.get_settings_controller()
        setctl.connect("plugin-enabled-changed", self._on_plugin_enabled)
        setctl.connect(
            "plugin-toplevel-changed", self._on_plugin_catalog_changed
        )

        self._load_all_plugins()
        dir_src, indir_src = self._get_directory_sources()
        sctr = get_source_controller()
        sctr.add(None, dir_src, toplevel=True)
        sctr.add(None, indir_src, toplevel=False)
        sctr.initialize()
        learn.load()

    def _on_display(self, _sched: ty.Any) -> None:
        self._reload_source_root()
        self._save_data_timer.set(DATA_SAVE_INTERVAL_S, self._save_data)

    def _get_directory_sources(
        self,
    ) -> tuple[tuple[DirectorySource, ...], tuple[DirectorySource, ...]]:
        """Return a tuple of dir_sources, indir_sources for directory sources
        directly included and for catalog inclusion respectively."""
        setctl = settings.get_settings_controller()
        source_config = setctl.get_config
        dir_depth = source_config("DeepDirectories", "Depth")

        def file_source(opt, depth=1):
            abs_path = os.path.abspath(os.path.expanduser(opt))
            return FileSource([abs_path], depth)

        indir_sources = itertools.chain(
            (
                DirectorySource(item, toplevel=True)
                for item in setctl.get_directories(False)
                if Path(item).is_dir()
            ),
            (
                file_source(item, dir_depth)
                for item in source_config("DeepDirectories", "Catalog")
            ),
        )

        dir_sources = itertools.chain(
            (
                DirectorySource(item, toplevel=True)
                for item in setctl.get_directories(True)
                if Path(item).is_dir()
            ),
            (
                file_source(item, dir_depth)
                for item in source_config("DeepDirectories", "Direct")
            ),
        )

        return tuple(dir_sources), tuple(indir_sources)

    def _load_all_plugins(self):
        """Insert all plugin sources into the catalog."""
        # pylint: disable=import-outside-toplevel
        from kupfer.core import plugins

        setctl = settings.get_settings_controller()
        for item in sorted(plugins.get_plugin_ids()):
            if setctl.get_plugin_enabled(item):
                sources_ = self._load_plugin(item)
                self._insert_sources(item, sources_, initialize=False)

    def _load_plugin(self, plugin_id: str) -> set[Source]:
        """Load @plugin_id, register all its Actions, Content and TextSources.
        Return its sources."""
        with pluginload.exception_guard(plugin_id):
            plugin = pluginload.load_plugin(plugin_id)
            self._register_text_sources(plugin_id, plugin.text_sources)
            self._register_action_decorators(
                plugin_id, plugin.action_decorators
            )
            self._register_content_decorators(
                plugin_id, plugin.content_decorators
            )
            self._register_action_generators(
                plugin_id, plugin.action_generators
            )
            return set(plugin.sources)

        return set()

    def _on_plugin_enabled(
        self, _setctl: ty.Any, plugin_id: str, enabled: bool | int
    ) -> None:
        """Enable plugin, load if necessary."""
        # pylint: disable=import-outside-toplevel
        from kupfer.core import plugins

        if enabled and not plugins.is_plugin_loaded(plugin_id):
            srcs = self._load_plugin(plugin_id)
            self._insert_sources(plugin_id, srcs, initialize=True)
        elif not enabled:
            self._remove_plugin(plugin_id)

    def _remove_plugin(self, plugin_id: str) -> None:
        sctl = get_source_controller()
        if sctl.remove_objects_for_plugin_id(plugin_id):
            self._reload_source_root()

        pluginload.remove_plugin(plugin_id)

    def _reload_source_root(self) -> None:
        """Reload items from root sources."""
        self.output_debug("Reloading source root")
        sctl = get_source_controller()
        if sctl.root:
            self._source_pane.source_rebase(sctl.root)

    def _on_plugin_catalog_changed(
        self, _setctl: ty.Any, _plugin_id: str, _toplevel: ty.Any
    ) -> None:
        self._reload_source_root()

    def _insert_sources(
        self,
        plugin_id: str,
        sources_: ty.Iterable[Source],
        initialize: bool = True,
    ) -> None:
        """Insert `sources_` into catalog. `Initialize` when True, initialize
        plugin and reload catalog root."""
        if not sources_:
            return

        sctl = get_source_controller()
        setctl = settings.get_settings_controller()
        for src in sources_:
            is_toplevel = setctl.get_source_is_toplevel(plugin_id, src)
            sctl.add(
                plugin_id, (src,), toplevel=is_toplevel, initialize=initialize
            )

        if initialize:
            self._reload_source_root()

    def _on_finish(self, _sched: ty.Any) -> None:
        "Close down the data model, save user data, and write caches to disk"
        get_source_controller().finalize()
        self._save_data(final_invocation=True)
        self.output_info("Saving cache...")
        get_source_controller().save_cache()

    def _save_data(self, final_invocation: bool = False) -> None:
        """Save Learning data and User's configuration data in sources
        (Recurring timer)."""
        self.output_info("Saving data...")
        learn.save()
        get_source_controller().save_data()
        if not final_invocation:
            self._save_data_timer.set(DATA_SAVE_INTERVAL_S, self._save_data)

    def _on_new_source(
        self, ctr: Pane[KupferObject], src: AnySource | None, select: ty.Any
    ) -> None:
        """Update leaf or secondary object panel on sources changes."""
        if not src:
            return

        if ctr is self._source_pane:
            pane = PaneSel.SOURCE
        elif ctr is self._object_pane:
            pane = PaneSel.OBJECT

        root = ctr.is_at_source_root()
        self.emit("source-changed", pane, src, root, select)

    def reset(self) -> None:
        self._source_pane.reset()
        self._action_pane.reset()
        self._object_pane.reset()

    def soft_reset(self, pane: PaneSel) -> AnySource | None:
        if pane == PaneSel.ACTION:
            return None

        panectl: LeafPane = self._get_panectl(pane)
        return panectl.soft_reset()

    def cancel_search(self, pane: PaneSel | None = None) -> None:
        """Cancel any outstanding search, or the search for @pane"""
        panes = (
            (pane,)
            if pane
            else (PaneSel.SOURCE, PaneSel.ACTION, PaneSel.OBJECT)
        )
        for pane_ in panes:
            ctl = self._get_panectl(pane_)
            if ctl.outstanding_search > 0:
                GLib.source_remove(ctl.outstanding_search)
                ctl.outstanding_search = -1

    def search(
        self,
        pane: PaneSel,
        key: str = "",
        context: str | None = None,
        interactive: bool = False,
        lazy: bool = False,
        text_mode: bool = False,
    ) -> None:
        """Search: Register the search method in the event loop

        Will search in @pane's base using @key, promising to return
        @context in the notification about the result.

        if @interactive, the search result will return immediately
        if @lazy, will slow down search result reporting
        """
        self.cancel_search(pane)
        self._latest_interaction = self._execution_context.last_command_id
        ctl = self._get_panectl(pane)
        ctl.outstanding_search_id = next(self._search_ids)
        wrapcontext = (ctl.outstanding_search_id, context)
        if interactive:
            ctl.search(key, wrapcontext, text_mode)
            return

        timeout = 300 if lazy else 0 if not key else 50 // len(key)

        def ctl_search(*args):
            ctl.outstanding_search = -1
            return ctl.search(*args)

        ctl.outstanding_search = GLib.timeout_add(
            timeout, ctl_search, key, wrapcontext, text_mode
        )

    def _on_pane_search_result(
        self,
        panectl: Pane[ty.Any],
        match: Rankable | None,
        match_iter: ty.Iterable[Rankable],
        wrapcontext: SearchContext,
        pane: PaneSel,
    ) -> bool:
        search_id, context = wrapcontext
        if search_id == panectl.outstanding_search_id:
            self.emit("search-result", pane, match, match_iter, context)
            return False

        self.output_debug("Skipping late search", match, context)
        return True

    def select(self, pane: PaneSel, item: KupferObject | None) -> None:
        """Select @item in @pane to self-update relevant places"""
        # If already selected, do nothing
        panectl = self._get_panectl(pane)
        if item == panectl.get_selection():
            return

        self.cancel_search()
        panectl.select(item)
        if pane == PaneSel.SOURCE:
            # populate actions
            citem = self._get_pane_object_composed(self._source_pane)
            self._action_pane.set_item(citem)
            self.search(PaneSel.ACTION, interactive=True)
            if self._mode == PaneMode.SOURCE_ACTION_OBJECT:
                self.object_stack_clear(PaneSel.OBJECT)
                self._populate_third_pane()

        elif pane == PaneSel.ACTION:
            assert item is None or isinstance(item, Action), str(type(item))
            self.object_stack_clear(PaneSel.OBJECT)
            if item and item.requires_object():
                newmode = PaneMode.SOURCE_ACTION_OBJECT
            else:
                newmode = PaneMode.SOURCE_ACTION

            if newmode != self._mode:
                self._mode = newmode
                self.emit("mode-changed", self._mode, item)

            if self._mode == PaneMode.SOURCE_ACTION_OBJECT:
                self._populate_third_pane()

    def _populate_third_pane(self) -> None:
        citem = self._get_pane_object_composed(self._source_pane)
        action = self._action_pane.get_selection()
        assert isinstance(action, Action)
        self._object_pane.set_item_and_action(citem, action)
        self.search(PaneSel.OBJECT, lazy=True)

    def get_can_enter_text_mode(self, pane: PaneSel) -> bool:
        panectl = self._get_panectl(pane)
        return panectl.get_can_enter_text_mode()

    def get_should_enter_text_mode(self, pane: PaneSel) -> bool:
        panectl = self._get_panectl(pane)
        return panectl.get_should_enter_text_mode()

    def validate(self) -> None:
        """Check if all selected items are still valid (for example after being
        spawned again, old item still focused).

        This will trigger .select() with None if items are not valid..
        """

        def valid_check(obj):
            return not (hasattr(obj, "is_valid") and not obj.is_valid())

        for pane, panectl in self._all_pane_ctl():
            sel = panectl.get_selection()
            if not valid_check(sel):
                self.emit("pane-reset", pane, None)
                self.select(pane, None)

            if self._has_object_stack(pane):
                new_stack = list(map(valid_check, panectl.object_stack))
                if new_stack != panectl.object_stack:
                    self._set_object_stack(pane, new_stack)

    def browse_up(self, pane: PaneSel) -> bool:
        """Try to browse up to previous sources, from current source"""
        if pane == PaneSel.SOURCE:
            return self._source_pane.browse_up()

        if pane == PaneSel.OBJECT:
            return self._object_pane.browse_up()

        return False

    def browse_down(self, pane: PaneSel, alternate: bool = False) -> None:
        """Browse into @leaf if it's possible and save away the previous sources
        in the stack. If @alternate, use the Source's alternate method"""
        if pane == PaneSel.ACTION:
            return

        # record used object if we browse down
        panectl = self._get_panectl(pane)
        sel, key = panectl.get_selection(), panectl.get_latest_key()
        if panectl.browse_down(alternate=alternate):
            learn.record_search_hit(sel, key)

    def activate(self, ui_ctx: GUIEnvironmentContext) -> None:
        """Activate current selection.

        @ui_ctx: GUI environment context object
        """
        leaf, action, sobject = self._get_current_command_objects()

        # register search to learning database
        learn.record_search_hit(leaf, self._source_pane.get_latest_key())
        learn.record_search_hit(action, self._action_pane.get_latest_key())
        if sobject and self._mode == PaneMode.SOURCE_ACTION_OBJECT:
            learn.record_search_hit(sobject, self._object_pane.get_latest_key())

        if not leaf or not action:
            return

        try:
            ctx = self._execution_context
            res, _ret = ctx.run(leaf, action, sobject, ui_ctx=ui_ctx)
        except commandexec.ActionExecutionError:
            self.output_exc()
            return

        if not res.is_sync:
            self.emit("launched-action", leaf, action, sobject)

    def execute_file(
        self,
        filepath: str,
        ui_ctx: GUIEnvironmentContext,
        on_error: ty.Callable[[ExecInfo], None],
    ) -> bool:
        """Execute a .kfcom file"""
        ctx = self._execution_context
        try:
            cmd_objs = execfile.parse_kfcom_file(filepath)
            assert len(cmd_objs) <= 3
            ctx.run(*cmd_objs, ui_ctx=ui_ctx)  # type: ignore
            return True
        except commandexec.ActionExecutionError:
            self.output_exc()
        except execfile.ExecutionError:
            on_error(sys.exc_info())

        return False

    def _insert_object(self, pane: PaneSel, obj: Leaf) -> None:
        """Insert @obj in @pane: prepare the object, then emit pane-reset"""
        self._decorate_object(obj)
        self.emit("pane-reset", pane, search.wrap_rankable(obj))

    def _decorate_object(self, *objects: Leaf) -> None:
        sctl = get_source_controller()
        for obj in objects:
            sctl.decorate_object(obj)

    def insert_objects(self, pane: PaneSel, objects: list[Leaf]) -> None:
        """Select @objects in @pane"""
        if pane != PaneSel.SOURCE:
            raise ValueError("Can only insert in first pane")

        self._decorate_object(*objects[:-1])
        self._set_object_stack(pane, objects[:-1])  # type: ignore
        self._insert_object(pane, objects[-1])

    def _on_command_execution_result(
        self,
        ctx: commandexec.ActionExecutionContext,
        result_type: commandexec.ExecResult | int,
        ret: ty.Any,
        uictx: GUIEnvironmentContext,
    ) -> None:
        result_type = commandexec.ExecResult(result_type)
        if result_type == commandexec.ExecResult.SOURCE:
            self.object_stack_clear_all()
            self._source_pane.push_source(ret)
        elif result_type == commandexec.ExecResult.OBJECT:
            self.object_stack_clear_all()
            self._insert_object(PaneSel.SOURCE, ret)
        elif result_type == commandexec.ExecResult.REFRESH:
            pass
        else:
            return

        self.emit("command-result", result_type, uictx)

    def _on_late_command_execution_result(
        self,
        ctx: commandexec.ActionExecutionContext,
        id_: int,
        result_type: commandexec.ExecResult | int,
        ret: ty.Any,
        uictx: GUIEnvironmentContext,
    ) -> None:
        """Receive late command result"""
        if self._latest_interaction < id_:
            self._on_command_execution_result(ctx, result_type, ret, uictx)

    def find_object(self, url: str) -> None:
        """Find object with URI @url and select it in the first pane"""
        sctrl = get_source_controller()
        qfu = qfurl.Qfurl(url=url)
        found = qfu.resolve_in_catalog(sctrl.get_sources())
        if found and not found == self._source_pane.get_selection():
            self._insert_object(PaneSel.SOURCE, found)

    def mark_as_default(self, pane: PaneSel) -> None:
        """Make the object selected on @pane as default for the selection in
        previous pane."""
        if pane in (PaneSel.SOURCE, PaneSel.OBJECT):
            raise RuntimeError("Setting default on pane 1 or 3 not supported")

        obj = self._source_pane.get_selection()
        act = self._action_pane.get_selection()
        assert obj and act
        assert isinstance(act, Leaf)
        assert isinstance(obj, Leaf)
        learn.set_correlation(act, obj)

    def get_object_has_affinity(self, pane: PaneSel) -> bool:
        """Return ``True`` if we have any recorded affinity for the object
        selected in @pane"""
        panectl = self._get_panectl(pane)
        if selection := panectl.get_selection():
            assert isinstance(selection, Leaf)
            return learn.get_object_has_affinity(selection)

        return False

    def erase_object_affinity(self, pane: PaneSel) -> None:
        """Erase all learned and configured affinity for the selection of
        @pane."""
        panectl = self._get_panectl(pane)
        if selection := panectl.get_selection():
            assert isinstance(selection, Leaf)
            learn.erase_object_affinity(selection)

    def compose_selection(self) -> None:
        leaf, action, iobj = self._get_current_command_objects()
        if leaf is None:
            return

        self.object_stack_clear_all()
        assert action
        obj = compose.ComposedLeaf(leaf, action, iobj)
        self._insert_object(PaneSel.SOURCE, obj)

    def _get_pane_object_composed(self, pane: Pane[Leaf]) -> Leaf | None:
        objects = list(pane.object_stack)
        sel = pane.get_selection()
        if sel and sel not in objects:
            objects.append(sel)

        if not objects:
            return None

        if len(objects) == 1:
            return objects[0]  # type: ignore

        return compose.MultipleLeaf(objects)

    def _get_current_command_objects(
        self,
    ) -> tuple[Leaf, Action, Leaf | None] | tuple[None, None, None]:
        """Return a tuple of current (obj, action, iobj)."""
        objects = self._get_pane_object_composed(self._source_pane)
        action: Action = self._action_pane.get_selection()  # type: ignore
        if objects is None or action is None:
            return (None, None, None)

        iobjects = self._get_pane_object_composed(self._object_pane)
        if self._mode == PaneMode.SOURCE_ACTION_OBJECT:
            if not iobjects:
                return (None, None, None)

        else:
            iobjects = None

        return (objects, action, iobjects)

    def _has_object_stack(self, pane: PaneSel) -> bool:
        return pane in (PaneSel.SOURCE, PaneSel.OBJECT)

    def _set_object_stack(
        self, pane: PaneSel, newstack: list[KupferObject]
    ) -> None:
        panectl = self._get_panectl(pane)
        panectl.object_stack = newstack
        self.emit("object-stack-changed", pane)

    def object_stack_push(self, pane: PaneSel, object_: KupferObject) -> bool:
        """Push @object_ onto the stack."""
        if not self._has_object_stack(pane):
            return False

        panectl = self._get_panectl(pane)
        if object_ not in panectl.object_stack:
            panectl.object_stack_push(object_)
            self.emit("object-stack-changed", pane)

        return True

    def object_stack_pop(self, pane: PaneSel) -> bool:
        if not self._has_object_stack(pane):
            return False

        panectl = self._get_panectl(pane)
        obj = panectl.object_stack_pop()
        self._insert_object(pane, obj)
        self.emit("object-stack-changed", pane)
        return True

    def object_stack_clear(self, pane: PaneSel) -> None:
        if not self._has_object_stack(pane):
            return

        panectl = self._get_panectl(pane)
        panectl.object_stack.clear()
        self.emit("object-stack-changed", pane)

    def object_stack_clear_all(self) -> None:
        """Clear the object stack for all panes."""
        # action don't have stack
        # self.object_stack_clear(PaneSel.ACTION)
        self.object_stack_clear(PaneSel.OBJECT)
        self.object_stack_clear(PaneSel.SOURCE)

    def get_object_stack(self, pane: PaneSel) -> list[KupferObject]:
        if not self._has_object_stack(pane):
            return []

        panectl = self._get_panectl(pane)
        return panectl.object_stack  # type: ignore


# pane cleared or set with new item
# pane, item
GObject.signal_new(
    "pane-reset",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (
        GObject.TYPE_INT,
        GObject.TYPE_PYOBJECT,
    ),
)

# pane, match, iter to matches, context
GObject.signal_new(
    "search-result",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (
        GObject.TYPE_INT,
        GObject.TYPE_PYOBJECT,
        GObject.TYPE_PYOBJECT,
        GObject.TYPE_PYOBJECT,
    ),
)

GObject.signal_new(
    "source-changed",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (int, object, bool, GObject.TYPE_PYOBJECT),
)

# mode, None(?)
GObject.signal_new(
    "mode-changed",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (
        GObject.TYPE_INT,
        GObject.TYPE_PYOBJECT,
    ),
)

# object stack update signal
# arguments: pane
GObject.signal_new(
    "object-stack-changed",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_INT,),
)
# when an command returned a result
# arguments: result type, gui_context
GObject.signal_new(
    "command-result",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_INT, GObject.TYPE_PYOBJECT),
)

# when an action was launched
# arguments: leaf, action, secondary leaf
GObject.signal_new(
    "launched-action",
    DataController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT),
)
