from abc import ABC, abstractmethod

class HideoutStrategyError(Exception):
    """Base exception for hideout strategy errors"""
    pass

class Strategy(ABC):
    @abstractmethod
    def __call__(self, poe_bot) -> None:
        pass 