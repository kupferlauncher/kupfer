"""
This file only exists for backwards compatibility!

For new plugins, you probably should not use ``commandexec``
at all, but instead implement ``Action.wants_context()``
"""
from kupfer.core.commandexec import *

import warnings
warnings.warn(FutureWarning("%s is deprecated. See Documentation/PluginAPI.rst" % __name__))

