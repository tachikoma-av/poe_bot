from utils.loot_filter import PickableItemLabel
from typing import List, Callable



class PickStrategy:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PickStrategy, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._arts_to_pick = [
            "Art/2DItems/Currency/CurrencyModValues.dds",  # divine
            "Art/2DItems/Currency/CurrencyGemQuality.dds",  # gemcutter
            "Art/2DItems/Currency/CurrencyRerollRare.dds",  # chaos
            "Art/2DItems/Currency/CurrencyAddModToRare.dds",  # exalt
            "Art/2DItems/Currency/CurrencyUpgradeToUnique.dds",  # chance
        ]
        
        # "Art/2DItems/Currency/Essence/GreaterFireEssence.dds"
        # Add big piles of gold
        for tier in range(2, 17):
            self._arts_to_pick.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds")
        
        # Add waystones
        for tier in range(1, 17):
            self._arts_to_pick.append(f"Art/2DItems/Maps/EndgameMaps/EndgameMap{tier}.dds")
    
    @property
    def arts_to_pick(self) -> List[str]:
        return self._arts_to_pick
    
    def should_pick_item(self, item_label: PickableItemLabel) -> bool:
        if item_label.icon_render in self._arts_to_pick:
            return True
        return False
    
    def add_art(self, art_path: str) -> None:
        """Add a new art path to pick list"""
        if art_path not in self._arts_to_pick:
            self._arts_to_pick.append(art_path)
    
    def remove_art(self, art_path: str) -> None:
        """Remove an art path from pick list"""
        if art_path in self._arts_to_pick:
            self._arts_to_pick.remove(art_path) 
            
class PickAllStrategy(PickStrategy):
    def should_pick_item(self, item_label: PickableItemLabel) -> bool:
        return True                