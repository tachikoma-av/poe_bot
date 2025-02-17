using System.Collections.Generic;

public class Posx1x2y1y2
{
    public int x1 { get; set; }
    public int x2 { get; set; }
    public int y1 { get; set; }
    public int y2 { get; set; }
}
public class PurchaseWindowHideout_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public List<InventoryObjectCustom_c> items { get; set; } // 
}
public class WorldMapUI_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
}
public class NpcDialogueUiChoice_c{
    public string text; // text
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
}
public class NpcDialogueUi_c{
    public int is_visible; // visible
    public List<NpcDialogueUiChoice_c> choices { get; set; } // choices, possible buttons we can click, [name, screen_zone]
    public List<InventoryObjectCustom_c> reward_choices { get; set; } // rewards choices
    public string npc_name; // npc_name
    public string text; // text
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
}
public class NpcRewardUi_c{
    public int visible; // visible
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
    public List<InventoryObjectCustom_c> choices { get; set; } // rewards choices

}

public class UltimatumNextWaveUi{
    public int is_visible; // visible
    public int accept_button_is_visible; // accept_button is visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public List<int> choices_label_screen_zone { get; set; } // choices label screen zone x1 x2 y1 y2
    public string round; // round
    public List<string> choices { get; set; } // choices
    public string is_trial_chosen; // if choice is made

}
public class PartyMember_c{
    public string ign { get; set; } // text
    public bool is_leader; // visible
    public string area_raw_name { get; set; } // text
    public bool same_location; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2

}
public class PartyInfo_c{
    public List<PartyMember_c> party_members { get; set; }
}

public class AuctionHouseUiOrder_c{
    public string offered_item { get; set; } // text
    public int offered_item_size { get; set; } // text
    public int offered_item_ratio { get; set; } // text
    public string wanted_item { get; set; } // text
    public int wanted_item_size { get; set; } // text
    public int wanted_item_ratio { get; set; } // text
    public int is_completed { get; set; } // text
    public int is_canceled { get; set; } // text
}

public class AuctionHouseUiCurrencyPickerCategory_c{
    public string text; // text
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    
}

public class AuctionHouseUiCurrencyPickerElements_c{
    public string text; // text
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public string count; // count
    
}

public class AuctionHouseUiCurrencyPicker_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public List<AuctionHouseUiCurrencyPickerCategory_c> categories { get; set; } // categories
    public List<AuctionHouseUiCurrencyPickerElements_c> presented_elements { get; set; } // presented elements
}

public class AuctionHouseUi_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // element screen zone x1 x2 y1 y2
    public List<int> i_want_button_screen_zone { get; set; } // i want button screen zone x1 x2 y1 y2
    public List<int> i_have_button_screen_zone { get; set; } // i have button screen zone x1 x2 y1 y2
    public string gold_in_inventory; // current gold
    public string i_have_item_name; // offered item type
    public string i_want_item_name; // wanted item type
    public string deal_cost_gold; // deal cost
    public List<int> place_order_button_screen_zone { get; set; } // place order button screen zone x1 x2 y1 y2
    public List<int> i_want_field_screen_zone { get; set; } // i want field screen zone x1 x2 y1 y2
    public List<int> i_have_field_screen_zone { get; set; } // i have field screen zone x1 x2 y1 y2
    public List<string> market_ratios_texts;
    public AuctionHouseUiCurrencyPicker_c currency_picker{ get; set; } // currency picker
    public List<AuctionHouseUiOrder_c> current_orders{ get; set; } // current orders
}

public class BlueLine_c{
    public string text { get; set; } // text
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public int is_visible; // visible
}
public class MapUi_c{
    public int is_visible; // visible
    public List<BlueLine_c> text_elements { get; set; } 
}
public class ResurrectUi_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
}

public class AnointUi_c{
    public int is_visible; // visible
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public List<InventoryObjectCustom_c> oils { get; set; } // oils
    public List<InventoryObjectCustom_c> placed_items { get; set; } // placed items
    public List<int> annoint_button_screen_zone { get; set; } // anoint button zone x1 x2 y1 y2
    public List<string> texts { get; set; } // texts

}

public class RitualUi_c{
    public int ritual_button_is_visible { get; set; } // ritual button is_visible
    public List<int> ritual_button_screen_zone { get; set; } // ritual button screen zone
    public string tribute { get; set; } // tribute
    public string progress { get; set; } // progress
    public int purchase_menu_is_visible { get; set; } // is_visible
    public List<int> purchase_menu_screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public string reroll_button_tooltip_text { get; set; } // reroll button tooltip raw
    public List<int> reroll_button_screen_zone { get; set; } // reroll button screen zone
    public string defer_button_text_raw { get; set; } // defer button text raw
    public List<int> defer_button_screen_zone { get; set; } // defer button screen zone
    public List<InventoryObjectCustom_c> items { get; set; } // items
    

}

public class AllUi_c{
    // public PurchaseWindowHideout_c pwh;
    // public WorldMapUI_c wm;
    // public NpcDialogueUi_c nd;
    // public NpcRewardUi_c nr;
    // public ResurrectUi_c ru;
    // public GetOpenedStashInfoObject inv; // inventory
    // public GetOpenedStashInfoObject sta; // stash
    // public InventoryObjectCustom_c hii; // hovered item info
}
public class VisibleLabel
{
    public string path { get; set; } // path
    public int id { get; set; } // id it belongs to
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public List<List<int>> screen_zones { get; set; } // array of screen zones label screen zone x1 x2 y1 y2
    public string item_metadata { get; set; } // item_metadata
    public List<string> texts { get; set; } // list of texts for this label
    public int is_visible { get; set; } // is visible
    public Posx1x2y1y2 p_o_s { get; set; } // pos_on_screen
}
public class SkillsOnBar_c
{
    public List<int> can_be_used { get; set; } // can_be_used 0 - false 1 - true
    public List<int> casts_per_100_seconds { get; set; } // casts per 100 seconds
    public List<int> total_uses { get; set; } // total uses
    // below if "full"
    public List<string> internal_name { get; set; } // internal_name
    public List<List<Dictionary<string, int>>> descriptions { get; set; } // descriptions
}
public class FlasksOnBar
{
    public List<string> flask_base_names { get; set; } // flask_base_names
    public List<int> can_use_flask { get; set; } // can_use_flask
    public List<int> flask_indexes { get; set; } // index
}
public class PlayerInfo_c
{
    public List<int> grid_position { get; set; } // player pos grid position x ,y 
    public List<int> life_component { get; set; } // life component, [health max,current,reserved, es max,current, reserved, mana max, current, reserved]
    public List<string> buffs { get; set; } // buffs
    public List<string> debuffs { get; set; } // debuffs
    public int is_moving { get; set; } // ismoving
    public int lvl { get; set; } // lvl
}
public class MinimapIcon_c
{
    public int id { get; set; } // id
    public string path { get; set; } // path
    public string name { get; set; } // name
    public int is_visible { get; set; } // is_hide
    public int is_hidden { get; set; } // is_visible
}


public class Entity_c{
    public List<int> location_on_screen { get; set; } // location on screen x,y
    public string path { get; set; } // path
    public string rarity { get; set; } // rarirty
    public int id { get; set; } // id
    public int is_opened { get; set; } // is opened
    public int is_hostile { get; set; } // is hostile
    public int is_attackable { get; set; } // is_attackable
    public int is_targetable { get; set; } // is targetable
    public int is_targeted { get; set; } // is_targeted
    public int essenced_mob { get; set; } // essenced_mob
    public int bound_center_pos { get; set; } // BoundsCenterPos
    public List<int> grid_position { get; set; } // grid position x, y
    public List<int> world_position { get; set; } // world position position x, y, z
    public List<int> life_component { get; set; } // life component, [health max,current,reserved, es max,current, reserved, mana max, current, reserved]
    public string render_name { get; set; } // render name
    public string entity_type { get; set; } // entity_type

}
public class VisibleLabelEntity_c{
    public List<int> location_on_screen { get; set; } // location on screen x,y
    public string path { get; set; } // path
    public int id { get; set; } // id
    public int is_targetable { get; set; } // is targetable
    public int bound_center_pos { get; set; } // BoundsCenterPos
    public List<int> grid_position { get; set; } // grid position x, y
    public List<int> world_position { get; set; } // world position position x, y, z
    public string render_name { get; set; } // render name
    public string entity_type { get; set; } // entity_type
}
public class ItemOnGroundLabel_c
{
    public int id; // id
    public List<int> greed_position { get; set; } // grid position x ,y 
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public string animated_property_metadata; // animated property metadata // itemonground -> components worlditem -> itementity -> components renderitem -> resourcepath
    public string rarity; // rarity
    public int is_targetable { get; set; } // is targetable
    public int is_targeted { get; set; } // is_targeted
    public string displayed_name { get; set; } // displayed name
}
public class QuestState_c{
    public string id; // id
    public int state; // id
}
public class GetDataObject
{
    public int broken_response { get; set; } // broken response
    public int game_state; // game state 0 - broken, 1 - main menu, 10 - select char, 20 - in game
    public List<int> window_borders { get; set; } // window borders x1 x2 y1 y2
    public List<int> mouse_cursor_pos { get; set; } // mouse cursor pos [x,y]
    public string terrain_string;
    public uint area_hash; // area hash
    public List<Entity_c> awake_entities { get; set; }
    public List<VisibleLabelEntity_c> visible_labels { get; set; } // visible labels
    public List<ItemOnGroundLabel_c> item_labels { get; set; } // item_labels
    public PlayerInfo_c player_info { get; set; } // player pos grid position x ,y
    public bool invites_panel_visible { get; set; } // Invites panel visible
    public bool IsLoading { get; set; }
    public bool IsLoading_b { get; set; }
    public string area_raw_name { get; set; }
    public FlasksOnBar flasks { get; set; }  // flasks
    public SkillsOnBar_c skills { get; set; }  // skills
    public List<int> mouse_grid_position { get; set; } // mouse grid position ingamestate.data.serverdata mouse world pos
    public int controller_type; // controller type
}
public class InventoryObjectCustom_c
{
    public string Name { get; set; }
    public string a { get; set; } // render_item_component.ResourcePath
    public string unique_name { get; set; }
    public string rarity { get; set; }
    public int map_tier { get; set; } // map_tier
    public int is_corrupted { get; set; } // corrupted
    public int is_identified { get; set; } // identified
    public string RenderArt { get; set; }
    public int items_in_stack { get; set; }
    public List<string> item_mods { get; set; }
    public List<string> item_mods_raw { get; set; } // item mods raw
    public List<string> l; // links ['rb', 'gb']
    public List<int> grid_position { get; set; } // grid pos x1x2y1y2
    public List<int> screen_zone { get; set; } // screenpos x1x2y1y2
    public List<string> tooltip_texts; // tooltip_texts
    public GridPosition_generated TopLeft { get; set; }
    public GridPosition_generated BottomRight { get; set; }
}
public class WorldMapEndGameMapObj
{
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    public int id { get; set; }
    public string name { get; set; }
    public string name_raw { get; set; }
    public List<string> icons { get; set; }
    public int can_run { get; set; }
}

public class GetMapDeviceInfoObject
{
    public bool atlas_panel_opened { get; set; } // atlas_panel_opened
    public bool world_map_opened { get; set; } // world_map_opened
    public List<WorldMapEndGameMapObj> availiable_maps { get; set; } // avaliable_maps
    public bool place_map_window_is_opened { get; set; } // place_map_window_opened
    public List<int> place_map_window_screen_zone { get; set; } // place_map_window_screenzone
    public string place_map_window_text { get; set; } // place_map_window_ text
    public List<InventoryObjectCustom_c> placed_items { get; set; } // place_map_window_items
    public List<int> place_map_window_activate_button_screen_zone { get; set; } // place map window activatte button screenzone
    public List<int> ziggurat_button_screen_zones { get; set; } // ziggurat button screenzone
    public List<List<int>> realmgate_screenzones { get; set; } // realmgate screenzones
}
public class GetOpenedStashInfoObject
{
    public string status { get; set; } // to remove
    public bool is_opened { get; set; }
    public List<int> location_on_screen { get; set; } // stash display position location on screen x,y
    public List<List<int>> tab_buttons_screen_zones { get; set; } // [ [x1,x2,y1,y2] ] for each stash tab button unsorted, [-1] is the "+"
    public string stash_tab_type { get; set; }
    public int total_stash_tab_count { get; set; }
    public int tab_index { get; set; }
    public List<InventoryObjectCustom_c> items { get; set; }
}
public class GridPosition_generated
{
    public int X { get; set; }
    public int Y { get; set; }
}

