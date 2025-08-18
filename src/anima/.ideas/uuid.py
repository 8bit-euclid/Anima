import json
import uuid
from abc import ABC, ABCMeta
from functools import cached_property


class MetaObject(ABCMeta, type):
    """
    Metaclass to add UUID generation capabilities to classes.

    This metaclass ensures:
    1. Each class gets a method to generate a deterministic UUID
    2. UUID is generated after full object initialization
    3. UUID is cached and consistent across calls
    """

    def __new__(mcs, name, bases, class_dict):
        def generate_deterministic_uuid(self):
            # Collect all attributes from the entire inheritance hierarchy
            full_state = {}

            # Traverse the Method Resolution Order (MRO) to collect attributes
            for cls in reversed(self.__class__.mro()):
                if hasattr(cls, "__dict__"):
                    for key, value in cls.__dict__.items():
                        if not key.startswith("_"):
                            full_state[f"{cls.__name__}_{key}"] = value

            # Add instance attributes
            for key, value in self.__dict__.items():
                full_state[key] = value
                # if not key.startswith('__'):
                #     full_state[key] = value

            # Convert to a consistent JSON representation
            state_str = json.dumps(full_state, sort_keys=True, default=str)

            # Use UUID5 with a consistent namespace
            return uuid.uuid5(uuid.NAMESPACE_DNS, state_str)

        # Add the UUID generation as a cached_property
        class_dict["uuid"] = cached_property(generate_deterministic_uuid)

        # Create the class
        return super().__new__(mcs, name, bases, class_dict)


class Object(ABC, metaclass=MetaObject):
    pass
