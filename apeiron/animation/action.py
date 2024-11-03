from collections import namedtuple
from abc import ABC, abstractmethod
from enum import Enum

Interval = namedtuple("Interval", ['start', 'stop'])


class Action(ABC):
    def __init__(self, interval: Interval):
        self.interval = interval

# class Type(Enum):
#     INTRO = 1
#     OUTRO = 2
#     TRANSLATE = 3
#     ROTATE = 4
#     GLOW = 5

# inline std::string
# ActionTypeString(const ActionType type)
# {
#    using AT = ActionType;
#    switch(type)
#    {
#       case AT::RampUp:             return "RampUp";
#       case AT::RampDown:           return "RampDown";
#       case AT::Scale:              return "Scale";
#       case AT::OffsetOrientation:  return "OffsetOrientation";
#       case AT::RotateBy:           return "RotateBy";
#       case AT::RotateAt:           return "RotateAt";
#       case AT::Reflect:            return "Reflect";
#       case AT::RevolveBy:          return "RevolveBy";
#       case AT::RevolveAt:          return "RevolveAt";
#       case AT::OffsetPosition:     return "OffsetPosition";
#       case AT::MoveBy:             return "MoveBy";
#       case AT::MoveTo:             return "MoveTo";
#       case AT::MoveAt:             return "MoveAt";
#       case AT::Trace:              return "Trace";
#       case AT::TrackPositionOf:    return "TrackPositionOf";
#       case AT::TrackOrientationOf: return "TrackOrientationOf";
#       case AT::MorphTo:            return "MorphTo";
#       case AT::MorphFrom:          return "MorphFrom";
#       case AT::SetStrokeColour:    return "SetStrokeColour";
#       case AT::SetFillColour:      return "SetFillColour";
#       case AT::Glow:               return "Glow";
#       case AT::Blink:              return "Blink";
#       default:                     throw std::invalid_argument("Unrecognised action type.");
#    }
# }
