from typing import List
from .base_strategy import Strategy

class HideoutPreparations:
    def __init__(self, strategies: List[Strategy]):
        self.strategies = strategies
        
    def __call__(self, poe_bot) -> None:
        for strategy in self.strategies:
            strategy(poe_bot) 