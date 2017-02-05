import pickle as pickle
import os

from kupfer import config
from kupfer import conspickle
from kupfer import pretty

mnemonics_filename = "mnemonics.pickle"
CORRELATION_KEY = 'kupfer.bonus.correlation'

## this is a harmless default
_default_actions = {
    '<builtin.AppLeaf gnome-terminal>': '<builtin.LaunchAgain>',
    '<builtin.AppLeaf xfce4-terminal>': '<builtin.LaunchAgain>',
}
_register = {}
_favorites = set()


class Mnemonics (object):
    """
    Class to describe a collection of mnemonics
    as well as the total count
    """
    def __init__(self):
        self.mnemonics = dict()
        self.count = 0
    def __repr__(self):
        return "<%s %d %s>" % (self.__class__.__name__, self.count, "".join(["%s: %d, " % (m,c) for m,c in self.mnemonics.items()]))
    def increment(self, mnemonic=None):
        if mnemonic:
            mcount = self.mnemonics.get(mnemonic, 0)
            self.mnemonics[mnemonic] = mcount + 1
        self.count += 1

    def decrement(self):
        """Decrement total count and the least mnemonic"""
        if self.mnemonics:
            key = min(self.mnemonics, key=lambda k: self.mnemonics[k])
            if self.mnemonics[key] <= 1:
                del self.mnemonics[key]
            else:
                self.mnemonics[key] -= 1
        self.count = max(self.count -1, 0)

    def __bool__(self):
        return self.count > 0
    def get_count(self):
        return self.count
    def get_mnemonics(self):
        return self.mnemonics

class Learning (object):
    @classmethod
    def _unpickle_register(cls, pickle_file):
        try:
            pfile = open(pickle_file, "rb")
        except IOError as e:
            return None
        try:
            data = conspickle.ConservativeUnpickler.loads(pfile.read())
            assert isinstance(data, dict), "Stored object not a dict"
            pretty.print_debug(__name__, "Reading from %s" % (pickle_file, ))
        except (pickle.PickleError, Exception) as e:
            data = None
            pretty.print_error(__name__, "Error loading %s: %s" % (pickle_file, e))
        finally:
            pfile.close()
        return data

    @classmethod
    def _pickle_register(self, reg, pickle_file):
        ## Write to tmp then rename over for atomicity
        tmp_pickle_file = "%s.%s" % (pickle_file, os.getpid())
        pretty.print_debug(__name__, "Saving to %s" % (pickle_file, ))
        with open(tmp_pickle_file, "wb") as output:
            output.write(pickle.dumps(reg, pickle.HIGHEST_PROTOCOL))
        os.rename(tmp_pickle_file, pickle_file)
        return True

def record_search_hit(obj, key=""):
    """
    Record that KupferObject @obj was used, with the optional
    search term @key recording
    """
    name = repr(obj)
    if name not in _register:
        _register[name] = Mnemonics()
    _register[name].increment(key)

def get_record_score(obj, key=""):
    """
    Get total score for KupferObject @obj,
    bonus score is given for @key matches
    """
    name = repr(obj)
    fav = 7 * (name in _favorites)
    if name not in _register:
        return fav
    mns = _register[name]
    if not key:
        cnt = mns.get_count()
        return fav + 50 * (1 - 1.0/(cnt + 1))

    stats = mns.get_mnemonics()
    closescr = sum(stats[m] for m in stats if m.startswith(key))
    mnscore = 30 * (1 - 1.0/(closescr + 1))
    exact = stats.get(key, 0)
    mnscore += 50 * (1 - 1.0/(exact + 1))
    return fav + mnscore


def get_correlation_bonus(obj, for_leaf):
    """
    Get the bonus rank for @obj when used with @for_leaf
    """
    if _register.setdefault(CORRELATION_KEY, {}).get(repr(for_leaf)) == repr(obj):
        return 50
    else:
        return 0

def set_correlation(obj, for_leaf):
    """
    Register @obj to get a bonus when used with @for_leaf
    """
    _register.setdefault(CORRELATION_KEY, {})[repr(for_leaf)] = repr(obj)

def _get_mnemonic_items(in_register):
    return [(k,v) for k,v in list(in_register.items()) if k != CORRELATION_KEY]

def get_object_has_affinity(obj):
    """
    Return if @obj has any positive score in the register
    """
    return bool(_register.get(repr(obj)) or
                _register.get(CORRELATION_KEY, {}).get(repr(obj)))

def erase_object_affinity(obj):
    """
    Remove all track of affinity for @obj
    """
    _register.pop(repr(obj), None)
    _register.get(CORRELATION_KEY, {}).pop(repr(obj), None)

def _prune_register():
    """
    Remove items with chance (len/25000)

    Assuming homogenous records (all with score one) we keep:
    x_n+1 := x_n * (1 - chance)

    To this we have to add the expected number of added mnemonics per
    invocation, est. 10, and we can estimate a target number of saved mnemonics.
    """
    import random
    random.seed()
    rand = random.random

    goalitems = 500
    flux = 2.0
    alpha = flux/goalitems**2

    chance = min(0.1, len(_register)*alpha)
    for leaf, mn in _get_mnemonic_items(_register):
        if rand() > chance:
            continue
        mn.decrement()
        if not mn:
            del _register[leaf]

    l = len(_register)
    pretty.print_debug(__name__, "Pruned register (%d mnemonics)" % l)

def load():
    """
    Load learning database
    """
    global _register

    filepath = config.get_config_file(mnemonics_filename)
    if filepath:
        _register = Learning._unpickle_register(filepath)
    if not _register:
        _register = {}
    if CORRELATION_KEY not in _register:
        _register[CORRELATION_KEY] = _default_actions

def save():
    """
    Save the learning record
    """
    if not _register:
        pretty.print_debug(__name__, "Not writing empty register")
        return
    if len(_register) > 100:
        _prune_register()
    filepath = config.save_config_file(mnemonics_filename)
    Learning._pickle_register(_register, filepath)

def add_favorite(obj):
    _favorites.add(repr(obj))

def remove_favorite(obj):
    _favorites.discard(repr(obj))

def is_favorite(obj):
    return repr(obj) in _favorites
