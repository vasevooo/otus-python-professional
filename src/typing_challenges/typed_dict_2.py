"""
TODO:

Define a class `Student` that represents a dictionary with three keys:
- name, a string
- age, an integer
- school, a string

Note: school can be optional
"""

from typing import TypedDict, NotRequired


class Student(TypedDict):
    name: str
    age: int
    school: NotRequired[str]
