"""
TODO:

Define a class `Student` that represents a dictionary with three keys:
- name, a string
- age, an integer
- school, a string
"""

from typing import TypedDict


class Student(TypedDict):
    name: str
    age: int
    school: str
