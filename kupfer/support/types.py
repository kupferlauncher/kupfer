#! /usr/bin/env python3

"""

"""
import types
import typing as ty

ExecInfo = ty.Union[
    tuple[
        ty.Type[BaseException], BaseException, ty.Optional[types.TracebackType]
    ],
    tuple[None, None, None],
]
