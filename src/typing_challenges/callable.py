"""
TODO:

Define a callable type that accepts a string argument and returns None.
*The parameter name can be arbitrary.*
"""

from collections.abc import Callable

SingleStringInput = Callable[[str], None]
