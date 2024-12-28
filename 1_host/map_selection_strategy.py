from typing import List, Optional
import random

class MapDeviceNotOpenError(Exception):
    """Raised when trying to select a map but the map device is not open"""
    pass

class SelectMapToRunStrategy:
    ALL_MAP_NAMES = [
            'MapAbyss_NoBoss',
            'MapBloomingField_NoBoss',
            'MapBurialBog_NoBoss',
            'MapCrimsonShores_NoBoss',
            'MapCrypt_NoBoss',
            'MapDecay_NoBoss',
            'MapForge_NoBoss',
            'MapFortress_NoBoss',
            'MapHideoutLimestone_Claimable',
            'MapHideoutShrine_Claimable',
            'MapHiddenGrotto_NoBoss',
            'MapHive_NoBoss',
            'MapMire_NoBoss',
            'MapOasis_NoBoss',
            'MapRiverside_NoBoss',
            'MapRustbowl_NoBoss',
            'MapSandspit_NoBoss',
            'MapSavanna_NoBoss',
            'MapSeepage_NoBoss',
            'MapSlick_NoBoss',
            'MapSteamingSprings_NoBoss',
            'MapSteppe_NoBoss',
            'MapSulphuricCaverns_NoBoss',
            'MapSump_NoBoss',
            'MapVaalFactory_NoBoss'
        ]
 
    def __init__(self, 
                 should_run_bosses: bool = False,
                 should_run_towers: bool = False,
                 ignored_map_names: Optional[List[str]] = None):
        self.should_run_bosses = should_run_bosses
        self.should_run_towers = should_run_towers
        self.ignored_map_names = ignored_map_names or []
    
    def select_map(self, map_device) -> any:  # Return type depends on map_device implementation
        """
        Select a map to run based on the strategy configuration.
        
        Args:
            map_device: The map device UI object that provides access to available maps
            
        Returns:
            Selected map object
            
        Raises:
            MapDeviceNotOpenError: If map device is not open
        """
        if not map_device.is_opened:
            raise MapDeviceNotOpenError("Map device must be open to select a map")
            
        possible_maps = []
        for map_obj in map_device.avaliable_maps:
            # Skip if it's a boss map and we don't want to run bosses
            if not self.should_run_bosses and map_obj.is_boss:
                continue
                
            # Skip if it's a tower map and we don't want to run towers
            if not self.should_run_towers and map_obj.is_tower:
                continue
                
            # Skip if the map name is in our ignore list
            if map_obj.name_raw in self.ignored_map_names:
                continue

            # Skip hideout maps
            if "Hideout" in map_obj.name_raw:
                continue
                
            possible_maps.append(map_obj)
            
        if not possible_maps:
            raise ValueError("No suitable maps found with current selection criteria")
            
        print(f"DEBUG: possible maps: {[m.name_raw for m in possible_maps]}")

        return random.choice(possible_maps) 