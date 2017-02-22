

import itertools
import operator
import os
import sys

from gi.repository import GLib, GObject

from kupfer.obj import base, sources, compose
from kupfer import pretty, scheduler
from kupfer import datatools
from kupfer.core import actioncompat
from kupfer.core import commandexec
from kupfer.core import execfile
from kupfer.core import pluginload
from kupfer.core import qfurl
from kupfer.core import search, learn
from kupfer.core import settings

from kupfer.core.sources import GetSourceController

# "Enums"
# Which pane
SourcePane, ActionPane, ObjectPane = (1,2,3)

# In two-pane or three-pane mode
SourceActionMode, SourceActionObjectMode = (1,2)

DATA_SAVE_INTERVAL_S = 3660

def identity(x):
    return x

def is_iterable(obj):
    return hasattr(obj, "__iter__")

def dress_leaves(seq, action):
    """yield items of @seq "dressed" by the source controller"""
    sc = GetSourceController()
    for itm in seq:
        sc.decorate_object(itm.object, action=action)
        yield itm

def peekfirst(seq):
    """This function will return (firstitem, iter)
    where firstitem is the first item of @seq or None if empty,
    and iter an equivalent copy of @seq
    """
    seq = iter(seq)
    for itm in seq:
        old_iter = itertools.chain((itm, ), seq)
        return (itm, old_iter)
    return (None, seq)

class Searcher (object):
    """
    This class searches KupferObjects efficiently, and
    stores searches in a cache for a very limited time (*)

    (*) As of this writing, the cache is used when the old key
    is a prefix of the search key.
    """

    def __init__(self):
        self._source_cache = {}
        self._old_key = None

    def search(self, sources, key, score=True, item_check=None, decorator=None):
        """
        @sources is a sequence listing the inputs, which should be
        Sources, TextSources or sequences of KupferObjects

        If @score, sort by rank.
        filters (with identity() as default):
            @item_check: Check items before adding to search pool
            @decorator: Decorate items before access

        Return (first, match_iter), where first is the first match,
        and match_iter an iterator to all matches, including the first match.
        """
        if not self._old_key or not key.startswith(self._old_key):
            self._source_cache.clear()
        self._old_key = key

        # General strategy: Extract a `list` from each source,
        # and perform ranking as in place operations on lists

        if not item_check: item_check = identity
        if not decorator: decorator = identity

        start_time = pretty.timing_start()
        match_lists = []
        for src in sources:
            fixedrank = 0
            can_cache = True
            rankables = None
            if is_iterable(src):
                items = item_check(src)
                can_cache = False
            else:
                # Look in source cache for stored rankables
                try:
                    rankables = self._source_cache[src]
                except KeyError:
                    try:
                        items = item_check(src.get_text_items(key))
                        fixedrank = src.get_rank()
                        can_cache = False
                    except AttributeError:
                        items = item_check(src.get_leaves())

            if rankables is None:
                rankables = search.make_rankables(items)

            if score:
                if fixedrank:
                    search.add_rank_objects(rankables, fixedrank)
                elif key:
                    search.score_objects(rankables, key)
                    search.bonus_objects(rankables, key)
                if can_cache:
                    self._source_cache[src] = rankables
            matches = rankables

            match_lists.append(matches)
        
        if score:
            matches = search.find_best_sort(match_lists)
        else:
            matches = itertools.chain(*match_lists)

        def as_set_iter(seq):
            key = operator.attrgetter("object")
            return datatools.UniqueIterator(seq, key=key)

        def valid_check(seq):
            """yield items of @seq that are valid"""
            for itm in seq:
                obj = itm.object
                if (not hasattr(obj, "is_valid")) or obj.is_valid():
                    yield itm

        # Check if the items are valid as the search
        # results are accessed through the iterators
        unique_matches = as_set_iter(matches)
        match, match_iter = peekfirst(decorator(valid_check(unique_matches)))
        pretty.timing_step(__name__, start_time, "ranked")
        return match, match_iter

    def rank_actions(self, objects, key, leaf, item_check=None, decorator=None):
        """
        rank @objects, which should be a sequence of KupferObjects,
        for @key, with the action ranker algorithm.

        @leaf is the Leaf the action is going to be invoked on

        Filters and return value like .score().
        """
        if not item_check: item_check = identity
        if not decorator: decorator = identity

        rankables = search.make_rankables(item_check(objects))
        if key:
            search.score_objects(rankables, key)
            matches = search.bonus_actions(rankables, key)
        else:
            matches = search.score_actions(rankables, leaf)
        matches = sorted(matches, key=operator.attrgetter("rank"), reverse=True)

        match, match_iter = peekfirst(decorator(matches))
        return match, match_iter

class Pane (GObject.GObject):
    """
    signals:
        search-result (match, match_iter, context)
    """
    __gtype_name__ = "Pane"
    def __init__(self):
        super(Pane, self).__init__()
        self.selection = None
        self.latest_key = None
        self.outstanding_search = -1
        self.outstanding_search_id = -1
        self.searcher = Searcher()

    def select(self, item):
        self.selection = item
    def get_selection(self):
        return self.selection
    def reset(self):
        self.selection = None
    def get_latest_key(self):
        return self.latest_key
    def get_can_enter_text_mode(self):
        return False
    def get_should_enter_text_mode(self):
        return False
    def emit_search_result(self, match, match_iter, context):
        self.emit("search-result", match, match_iter, context)

GObject.signal_new("search-result", Pane, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, 
        GObject.TYPE_PYOBJECT))

class LeafPane (Pane, pretty.OutputMixin):
    __gtype_name__ = "LeafPane"

    def __init__(self):
        super(LeafPane, self).__init__()
        self.source_stack = []
        self.source = None
        self.object_stack = []

    def select(self, item):
        assert item is None or isinstance(item, base.Leaf), \
                    "New selection for object pane is not a Leaf!"
        super().select(item)

    def _load_source(self, src):
        """Try to get a source from the SourceController,
        if it is already loaded we get it from there, else
        returns @src"""
        sc = GetSourceController()
        return sc.get_canonical_source(src)

    def get_source(self):
        return self.source

    def source_rebase(self, src):
        self.source_stack = []
        self.source = self._load_source(src)
        self.refresh_data()

    def push_source(self, src):
        self.source_stack.append(self.source)
        self.source = self._load_source(src)
        self.refresh_data()

    def pop_source(self):
        """Return True if succeeded"""
        if not len(self.source_stack):
            return False
        self.source = self.source_stack.pop()
        return True

    def is_at_source_root(self):
        """Return True if we have no source stack"""
        return not self.source_stack

    def object_stack_push(self, obj):
        self.object_stack.append(obj)

    def object_stack_pop(self):
        return self.object_stack.pop()

    def get_can_enter_text_mode(self):
        return self.is_at_source_root()

    def get_should_enter_text_mode(self):
        return False

    def refresh_data(self):
        self.emit("new-source", self.source)

    def browse_up(self):
        """Try to browse up to previous sources, from current
        source"""
        succ = self.pop_source()
        if not succ:
            if self.source.has_parent():
                self.source_rebase(self.source.get_parent())
                succ = True
        if succ:
            self.refresh_data()
        return succ

    def browse_down(self, alternate=False):
        """Browse into @leaf if it's possible
        and save away the previous sources in the stack
        if @alternate, use the Source's alternate method"""
        leaf = self.get_selection()
        if leaf and leaf.has_content():
            self.push_source(leaf.content_source(alternate=alternate))
            return True
        return False

    def reset(self):
        """Pop all sources and go back to top level"""
        Pane.reset(self)
        while self.pop_source():
            pass
        self.refresh_data()

    def soft_reset(self):
        Pane.reset(self)
        while self.pop_source():
            pass
        return self.source

    def search(self, key="", context=None, text_mode=False):
        """
        filter for action @item
        """
        self.latest_key = key
        sources = [ self.get_source() ] if not text_mode else []
        if key and self.is_at_source_root():
            # Only use text sources when we are at root catalog
            sc = GetSourceController()
            textsrcs = sc.get_text_sources()
            sources.extend(textsrcs)

        decorator = lambda seq: dress_leaves(seq, action=None)
        match, match_iter = self.searcher.search(sources, key, score=bool(key),
                decorator=decorator)
        self.emit_search_result(match, match_iter, context)

GObject.signal_new("new-source", LeafPane, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT,))

class PrimaryActionPane (Pane):
    def __init__(self):
        super(PrimaryActionPane, self).__init__()
        self.set_item(None)

    def select(self, item):
        assert not item or isinstance(item, base.Action), \
                "Selection in action pane is not an Action!"
        super().select(item)

    def set_item(self, item):
        """Set which @item we are currently listing actions for"""
        self.current_item = item
        self._action_valid_cache = {}

    def search(self, key="", context=None, text_mode=False):
        """Search: Register the search method in the event loop

        using @key, promising to return
        @context in the notification about the result, having selected
        @item in SourcePane

        If we already have a call to search, we remove the "source"
        so that we always use the most recently requested search."""

        self.latest_key = key
        leaf = self.current_item
        actions = actioncompat.actions_for_item(leaf, GetSourceController())

        def is_valid_cached(action):
            """Check if @action is valid for current item"""
            cache = self._action_valid_cache
            valid = cache.get(action)
            if valid is None:
                valid = actioncompat.action_valid_for_item(action, leaf)
                cache[action] = valid
            return valid

        def valid_decorator(seq):
            """Check if actions are valid before access"""
            for obj in seq:
                if is_valid_cached(obj.object):
                    yield obj

        match, match_iter = self.searcher.rank_actions(actions, key, leaf,
                decorator=valid_decorator)
        self.emit_search_result(match, match_iter, context)

class SecondaryObjectPane (LeafPane):
    __gtype_name__ = "SecondaryObjectPane"
    def __init__(self):
        LeafPane.__init__(self)
        self.current_item = None
        self.current_action = None

    def reset(self):
        LeafPane.reset(self)
        self.searcher = Searcher()

    def set_item_and_action(self, item, act):
        self.current_item = item
        self.current_action = act
        if item and act:
            ownsrc, use_catalog = actioncompat.iobject_source_for_action(act, item)
            if ownsrc and not use_catalog:
                self.source_rebase(ownsrc)
            else:
                extra_sources = [ownsrc] if ownsrc else ()
                sc = GetSourceController()
                self.source_rebase(sc.root_for_types(act.object_types(), extra_sources))
        else:
            self.reset()

    def get_can_enter_text_mode(self):
        """Check if there are any reasonable text sources for this action"""
        atroot = self.is_at_source_root()
        types = tuple(self.current_action.object_types())
        sc = GetSourceController()
        textsrcs = sc.get_text_sources()
        return (atroot and
            any(sc.good_source_for_types(s, types) for s in textsrcs))

    def get_should_enter_text_mode(self):
        return (self.is_at_source_root() and
                hasattr(self.get_source(), "get_text_items"))

    def search(self, key="", context=None, text_mode=False):
        """
        filter for action @item
        """
        self.latest_key = key
        sources = []
        if not text_mode or hasattr(self.get_source(), "get_text_items"):
            sources.append(self.get_source())
        if key and self.is_at_source_root():
            # Only use text sources when we are at root catalog
            sc = GetSourceController()
            textsrcs = sc.get_text_sources()
            sources.extend(textsrcs)

        item_check = actioncompat.iobjects_valid_for_action(self.current_action,
                self.current_item)
        decorator = lambda seq: dress_leaves(seq, action=self.current_action)

        match, match_iter = self.searcher.search(sources, key, score=True,
                item_check=item_check, decorator=decorator)
        self.emit_search_result(match, match_iter, context)

class DataController (GObject.GObject, pretty.OutputMixin):
    """
    Sources <-> Actions controller

    The data controller must be created before main program commences,
    so it can register itself at the scheduler correctly.
    """
    __gtype_name__ = "DataController"

    def __init__(self):
        super(DataController, self).__init__()

        self.source_pane = LeafPane()
        self.object_pane = SecondaryObjectPane()
        self.source_pane.connect("new-source", self._new_source)
        self.object_pane.connect("new-source", self._new_source)
        self.action_pane = PrimaryActionPane()
        self._panectl_table = {
            SourcePane : self.source_pane,
            ActionPane : self.action_pane,
            ObjectPane : self.object_pane,
            }
        for pane, ctl in list(self._panectl_table.items()):
            ctl.connect("search-result", self._pane_search_result, pane)
        self.mode = None
        self._search_ids = itertools.count(1)
        self._latest_interaction = -1
        self._execution_context = commandexec.DefaultActionExecutionContext()
        self._execution_context.connect("command-result",
                self._command_execution_result)
        self._execution_context.connect("late-command-result",
                self._late_command_execution_result)

        self._save_data_timer = scheduler.Timer()

        sch = scheduler.GetScheduler()
        sch.connect("load", self._load)
        sch.connect("display", self._display)
        sch.connect("finish", self._finish)

    def register_text_sources(self, plugin_id, srcs):
        """Pass in text sources as @srcs

        we register text sources """
        sc = GetSourceController()
        sc.add_text_sources(plugin_id, srcs)
    
    def register_action_decorators(self, plugin_id, actions):
        # Keep a mapping: Decorated Leaf Type -> List of actions
        decorate_types = {}
        for action in actions:
            for appl_type in action.item_types():
                decorate_types.setdefault(appl_type, []).append(action)
        if not decorate_types:
            return
        sc = GetSourceController()
        sc.add_action_decorators(plugin_id, decorate_types)

    def register_content_decorators(self, plugin_id, contents):
        """
        Register the sequence of classes @contents as
        potential content decorators. Classes not conforming to
        the decoration protocol (most importantly, ``.decorates_type()``)
        will be skipped
        """
        # Keep a mapping:
        # Decorated Leaf Type -> Set of content decorator types
        decorate_item_types = {}
        for c in contents:
            try:
                applies = c.decorates_type()
            except AttributeError:
                continue
            decorate_item_types.setdefault(applies, set()).add(c)
        if not decorate_item_types:
            return
        sc = GetSourceController()
        sc.add_content_decorators(plugin_id, decorate_item_types)

    def register_action_generators(self, plugin_id, generators):
        sc = GetSourceController()
        for generator in generators:
            sc.add_action_generator(plugin_id, generator)

    def _load(self, sched):
        """Begin Data Controller work when we get application 'load' signal

        Load the data model from saved configuration and caches
        """
        setctl = settings.GetSettingsController()
        setctl.connect("plugin-enabled-changed", self._plugin_enabled)
        setctl.connect("plugin-toplevel-changed", self._plugin_catalog_changed)

        self._load_all_plugins()
        D_s, d_s = self._get_directory_sources()
        sc = GetSourceController()
        sc.add(None, D_s, toplevel=True)
        sc.add(None, d_s, toplevel=False)
        sc.initialize()
        learn.load()

    def _display(self, sched):
        self._reload_source_root()
        self._save_data_timer.set(DATA_SAVE_INTERVAL_S, self._save_data)

    def _get_directory_sources(self):
        """
        Return a tuple of S_sources, s_sources for
        directory sources directly included and for
        catalog inclusion respectively
        """

        s_sources = []
        S_sources = []

        setctl = settings.GetSettingsController()
        source_config = setctl.get_config

        def dir_source(opt):
            return sources.DirectorySource(opt)

        def file_source(opt, depth=1):
            abs = os.path.abspath(os.path.expanduser(opt))
            return sources.FileSource((abs,), depth)

        for coll, direct in zip((s_sources, S_sources), (False, True)):
            for item in setctl.get_directories(direct):
                if not os.path.isdir(item):
                    continue
                coll.append(dir_source(item))

        dir_depth = source_config("DeepDirectories", "Depth")

        for item in source_config("DeepDirectories","Catalog"):
            s_sources.append(file_source(item, dir_depth))
        for item in source_config("DeepDirectories", "Direct"):
            S_sources.append(file_source(item, dir_depth))

        return S_sources, s_sources

    def _load_all_plugins(self):
        """
        Insert all plugin sources into the catalog
        """
        from kupfer.core import plugins

        setctl = settings.GetSettingsController()
        for item in sorted(plugins.get_plugin_ids()):
            if not setctl.get_plugin_enabled(item):
                continue
            sources = self._load_plugin(item)
            self._insert_sources(item, sources, initialize=False)

    def _load_plugin(self, plugin_id):
        """
        Load @plugin_id, register all its Actions, Content and TextSources.
        Return its sources.
        """
        with pluginload.exception_guard(plugin_id):
            plugin = pluginload.load_plugin(plugin_id)
            self.register_text_sources(plugin_id, plugin.text_sources)
            self.register_action_decorators(plugin_id, plugin.action_decorators)
            self.register_content_decorators(plugin_id, plugin.content_decorators)
            self.register_action_generators(plugin_id, plugin.action_generators)
            return set(plugin.sources)
        return set()

    def _plugin_enabled(self, setctl, plugin_id, enabled):
        from kupfer.core import plugins
        if enabled and not plugins.is_plugin_loaded(plugin_id):
            sources = self._load_plugin(plugin_id)
            self._insert_sources(plugin_id, sources, initialize=True)
        elif not enabled:
            self._remove_plugin(plugin_id)

    def _remove_plugin(self, plugin_id):
        sc = GetSourceController()
        if sc.remove_objects_for_plugin_id(plugin_id):
            self._reload_source_root()
        pluginload.remove_plugin(plugin_id)

    def _reload_source_root(self):
        self.output_debug("Reloading source root")
        sc = GetSourceController()
        self.source_pane.source_rebase(sc.root)

    def _plugin_catalog_changed(self, setctl, plugin_id, toplevel):
        self._reload_source_root()

    def _insert_sources(self, plugin_id, sources, initialize=True):
        if not sources:
            return
        sc = GetSourceController()
        setctl = settings.GetSettingsController()
        for src in sources:
            is_toplevel = setctl.get_source_is_toplevel(plugin_id, src)
            sc.add(plugin_id, (src, ), toplevel=is_toplevel,
                   initialize=initialize)
        if initialize:
            self._reload_source_root()

    def _finish(self, sched):
        "Close down the data model, save user data, and write caches to disk"
        GetSourceController().finalize()
        self._save_data(final_invocation=True)
        self.output_info("Saving cache...")
        GetSourceController().save_cache()

    def _save_data(self, final_invocation=False):
        """Save Learning data and User's configuration data in sources
        (Recurring timer)
        """
        self.output_info("Saving data...")
        learn.save()
        GetSourceController().save_data()
        if not final_invocation:
            self._save_data_timer.set(DATA_SAVE_INTERVAL_S, self._save_data)

    def _new_source(self, ctr, src):
        if ctr is self.source_pane:
            pane = SourcePane
        elif ctr is self.object_pane:
            pane = ObjectPane
        root = ctr.is_at_source_root()
        self.emit("source-changed", pane, src, root)

    def reset(self):
        self.source_pane.reset()
        self.action_pane.reset()

    def soft_reset(self, pane):
        if pane is ActionPane:
            return
        panectl = self._panectl_table[pane]
        return panectl.soft_reset()

    def cancel_search(self, pane=None):
        """Cancel any outstanding search, or the search for @pane"""
        panes = (pane, ) if pane else iter(self._panectl_table)
        for pane in panes:
            ctl = self._panectl_table[pane]
            if ctl.outstanding_search > 0:
                GLib.source_remove(ctl.outstanding_search)
                ctl.outstanding_search = -1

    def search(self, pane, key="", context=None, interactive=False, lazy=False,
            text_mode=False):
        """Search: Register the search method in the event loop

        Will search in @pane's base using @key, promising to return
        @context in the notification about the result.

        if @interactive, the search result will return immediately
        if @lazy, will slow down search result reporting
        """

        self.cancel_search(pane)
        self._latest_interaction = self._execution_context.last_command_id
        ctl = self._panectl_table[pane]
        ctl.outstanding_search_id = next(self._search_ids)
        wrapcontext = (ctl.outstanding_search_id, context)
        if interactive:
            ctl.search(key, wrapcontext, text_mode)
        else:
            timeout = 300 if lazy else 0 if not key else 50//len(key)

            def ctl_search(*args):
                ctl.outstanding_search = -1
                return ctl.search(*args)
            ctl.outstanding_search = GLib.timeout_add(timeout, ctl_search,
                    key, wrapcontext, text_mode)

    def _pane_search_result(self, panectl, match,match_iter, wrapcontext, pane):
        search_id, context = wrapcontext
        if not search_id is panectl.outstanding_search_id:
            self.output_debug("Skipping late search", match, context)
            return True
        self.emit("search-result", pane, match, match_iter, context)

    def select(self, pane, item):
        """Select @item in @pane to self-update
        relevant places"""
        # If already selected, do nothing
        panectl = self._panectl_table[pane]
        if item == panectl.get_selection():
            return
        self.cancel_search()
        panectl.select(item)
        if pane is SourcePane:
            # populate actions
            citem = self._get_pane_object_composed(self.source_pane)
            self.action_pane.set_item(citem)
            self.search(ActionPane, interactive=True)
            if self.mode == SourceActionObjectMode:
                self.object_stack_clear(ObjectPane)
                self._populate_third_pane()
        elif pane is ActionPane:
            self.object_stack_clear(ObjectPane)
            if item and item.requires_object():
                newmode = SourceActionObjectMode
            else:
                newmode = SourceActionMode
            if newmode != self.mode:
                self.mode = newmode
                self.emit("mode-changed", self.mode, item)
            if self.mode == SourceActionObjectMode:
                self._populate_third_pane()
        elif pane is ObjectPane:
            pass

    def _populate_third_pane(self):
        citem = self._get_pane_object_composed(self.source_pane)
        action = self.action_pane.get_selection()
        self.object_pane.set_item_and_action(citem, action)
        self.search(ObjectPane, lazy=True)

    def get_can_enter_text_mode(self, pane):
        panectl = self._panectl_table[pane]
        return panectl.get_can_enter_text_mode()

    def get_should_enter_text_mode(self, pane):
        panectl = self._panectl_table[pane]
        return panectl.get_should_enter_text_mode()

    def validate(self):
        """Check if all selected items are still valid
        (for example after being spawned again, old item
        still focused)

        This will trigger .select() with None if items
        are not valid..
        """
        def valid_check(obj):
            return not (hasattr(obj, "is_valid") and not obj.is_valid())

        for pane, panectl in list(self._panectl_table.items()):
            sel = panectl.get_selection()
            if not valid_check(sel):
                self.emit("pane-reset", pane, None)
                self.select(pane, None)
            if self._has_object_stack(pane):
                new_stack = [o for o in panectl.object_stack if valid_check(o)]
                if new_stack != panectl.object_stack:
                    self._set_object_stack(pane, new_stack)

    def browse_up(self, pane):
        """Try to browse up to previous sources, from current
        source"""
        if pane is SourcePane:
            return self.source_pane.browse_up()
        if pane is ObjectPane:
            return self.object_pane.browse_up()
    
    def browse_down(self, pane, alternate=False):
        """Browse into @leaf if it's possible
        and save away the previous sources in the stack
        if @alternate, use the Source's alternate method"""
        if pane is ActionPane:
            return
        # record used object if we browse down
        panectl = self._panectl_table[pane]
        sel, key = panectl.get_selection(), panectl.get_latest_key()
        if panectl.browse_down(alternate=alternate):
            learn.record_search_hit(sel, key)

    def activate(self, ui_ctx):
        """
        Activate current selection

        @ui_ctx: GUI environment context object
        """
        leaf, action, sobject = self._get_current_command_objects()

        # register search to learning database
        learn.record_search_hit(leaf, self.source_pane.get_latest_key())
        learn.record_search_hit(action, self.action_pane.get_latest_key())
        if sobject and self.mode is SourceActionObjectMode:
            learn.record_search_hit(sobject, self.object_pane.get_latest_key())

        try:
            ctx = self._execution_context
            res, ret = ctx.run(leaf, action, sobject, ui_ctx=ui_ctx)
        except commandexec.ActionExecutionError:
            self.output_exc()
            return

        if res not in commandexec.RESULTS_SYNC:
            self.emit("launched-action")

    def execute_file(self, filepath, ui_ctx, on_error):
        try:
            cmd_objs = execfile.parse_kfcom_file(filepath)
            ctx = self._execution_context
            ctx.run(*cmd_objs, ui_ctx=ui_ctx)
            return True
        except commandexec.ActionExecutionError:
            self.output_exc()
            return
        except execfile.ExecutionError:
            on_error(sys.exc_info())
            return False

    def _insert_object(self, pane, obj):
        "Insert @obj in @pane: prepare the object, then emit pane-reset"
        self._decorate_object(obj)
        self.emit("pane-reset", pane, search.wrap_rankable(obj))

    def _decorate_object(self, *objects):
        sc = GetSourceController()
        for obj in objects:
            sc.decorate_object(obj)

    def insert_objects(self, pane, objects):
        "Select @objects in @pane"
        if pane != SourcePane:
            raise ValueError("Can only insert in first pane")
        self._decorate_object(objects[:-1])
        self._set_object_stack(pane, objects[:-1])
        self._insert_object(pane, objects[-1])

    def _command_execution_result(self, ctx, result_type, ret, uictx):
        if result_type == commandexec.RESULT_SOURCE:
            self.object_stack_clear_all()
            self.source_pane.push_source(ret)
        elif result_type == commandexec.RESULT_OBJECT:
            self.object_stack_clear_all()
            self._insert_object(SourcePane, ret)
        else:
            return
        self.emit("command-result", result_type, uictx)

    def _late_command_execution_result(self, ctx, id_, result_type, ret, uictx):
        "Receive late command result"
        if self._latest_interaction < id_:
            self._command_execution_result(ctx, result_type, ret, uictx)

    def find_object(self, url):
        """Find object with URI @url and select it in the first pane"""
        sc = GetSourceController()
        qf = qfurl.qfurl(url=url)
        found = qf.resolve_in_catalog(sc.sources)
        if found and not found == self.source_pane.get_selection():
            self._insert_object(SourcePane, found)

    def mark_as_default(self, pane):
        """
        Make the object selected on @pane as default
        for the selection in previous pane.
        """
        if pane is SourcePane or pane is ObjectPane:
            raise RuntimeError("Setting default on pane 1 or 3 not supported")
        obj = self.source_pane.get_selection()
        act = self.action_pane.get_selection()
        assert obj and act
        learn.set_correlation(act, obj)

    def get_object_has_affinity(self, pane):
        """
        Return ``True`` if we have any recorded affinity
        for the object selected in @pane
        """
        panectl = self._panectl_table[pane]
        selection = panectl.get_selection()
        if not selection:
            return None
        return learn.get_object_has_affinity(selection)

    def erase_object_affinity(self, pane):
        """
        Erase all learned and configured affinity for
        the selection of @pane
        """
        panectl = self._panectl_table[pane]
        selection = panectl.get_selection()
        if not selection:
            return None
        return learn.erase_object_affinity(selection)

    def compose_selection(self):
        leaf, action, iobj = self._get_current_command_objects()
        if leaf is None:
            return
        self.object_stack_clear_all()
        obj = compose.ComposedLeaf(leaf, action, iobj)
        self._insert_object(SourcePane, obj)

    def _get_pane_object_composed(self, pane):
        objects = list(pane.object_stack)
        sel = pane.get_selection()
        if sel and sel not in objects:
            objects.append(sel)
        if not objects:
            return None
        elif len(objects) == 1:
            return objects[0]
        else:
            return compose.MultipleLeaf(objects)

    def _get_current_command_objects(self):
        """
        Return a tuple of current (obj, action, iobj)
        """
        objects = self._get_pane_object_composed(self.source_pane)
        action = self.action_pane.get_selection()
        if objects is None or action is None:
            return (None, None, None)
        iobjects = self._get_pane_object_composed(self.object_pane)
        if self.mode == SourceActionObjectMode:
            if not iobjects:
                return (None, None, None)
        else:
            iobjects = None
        return (objects, action, iobjects)

    def _has_object_stack(self, pane):
        return pane in (SourcePane, ObjectPane)

    def _set_object_stack(self, pane, newstack):
        panectl = self._panectl_table[pane]
        panectl.object_stack[:] = list(newstack)
        self.emit("object-stack-changed", pane)

    def object_stack_push(self, pane, object_):
        """
        Push @object_ onto the stack
        """
        if not self._has_object_stack(pane):
            return
        panectl = self._panectl_table[pane]
        if object_ not in panectl.object_stack:
            panectl.object_stack_push(object_)
            self.emit("object-stack-changed", pane)
        return True

    def object_stack_pop(self, pane):
        if not self._has_object_stack(pane):
            return
        panectl = self._panectl_table[pane]
        obj = panectl.object_stack_pop()
        self._insert_object(pane, obj)
        self.emit("object-stack-changed", pane)
        return True

    def object_stack_clear(self, pane):
        if not self._has_object_stack(pane):
            return
        panectl = self._panectl_table[pane]
        panectl.object_stack[:] = []
        self.emit("object-stack-changed", pane)

    def object_stack_clear_all(self):
        """
        Clear the object stack for all panes
        """
        for pane in self._panectl_table:
            self.object_stack_clear(pane)

    def get_object_stack(self, pane):
        if not self._has_object_stack(pane):
            return ()
        panectl = self._panectl_table[pane]
        return panectl.object_stack

# pane cleared or set with new item
# pane, item
GObject.signal_new("pane-reset", DataController, GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN, (GObject.TYPE_INT, GObject.TYPE_PYOBJECT,))

# pane, match, iter to matches, context
GObject.signal_new("search-result", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_INT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))

GObject.signal_new("source-changed", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (int, object, bool))

# mode, None(?)
GObject.signal_new("mode-changed", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_INT, GObject.TYPE_PYOBJECT,))

# object stack update signal
# arguments: pane
GObject.signal_new("object-stack-changed", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_INT, ))
# when an command returned a result
# arguments: result type, gui_context
GObject.signal_new("command-result", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, (GObject.TYPE_INT, GObject.TYPE_PYOBJECT))

# when an action was launched
# arguments: none
GObject.signal_new("launched-action", DataController, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())


