"""
Various, common types for typechecing
"""

import types
import typing as ty

ExecInfo = ty.Union[
    tuple[
        ty.Type[BaseException], BaseException, ty.Optional[types.TracebackType]
    ],
    tuple[None, None, None],
]
