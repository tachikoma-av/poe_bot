using System.Collections.Generic;
using Newtonsoft.Json;

// to increase performance by reducing the size of json response
// objects are serialized for json response https://eliot-jones.com/2014/9/minify-json-net
// serialization includes:
// reducing property names
// converting bools into integers
// storing some data as list rather than objects (screen zones/life/positions)


public class Posx1x2y1y2
{
    public int x1 { get; set; }
    public int x2 { get; set; }
    public int y1 { get; set; }
    public int y2 { get; set; }
}
public class PurchaseWindowHideout_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("items")]
    public List<InventoryObjectCustom_c> items { get; set; } // 
}
public class WorldMapUI_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
}
public class NpcDialogueUiChoice_c{
    [JsonProperty("t")]
    public string text; // text
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
}
public class NpcDialogueUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("ch")]
    public List<NpcDialogueUiChoice_c> choices { get; set; } // choices, possible buttons we can click, [name, screen_zone]
    [JsonProperty("rw")]
    public List<InventoryObjectCustom_c> reward_choices { get; set; } // rewards choices
    [JsonProperty("nn")]
    public string npc_name; // npc_name
    [JsonProperty("t")]
    public string text; // text
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
}
public class NpcRewardUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // screen zone x1 x2 y1 y2
    [JsonProperty("choices")]
    public List<InventoryObjectCustom_c> choices { get; set; } // rewards choices
}

public class UltimatumNextWaveUi{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("a_b_v")]
    public int accept_button_is_visible; // accept_button is visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("ch_sz")]
    public List<int> choices_label_screen_zone { get; set; } // choices label screen zone x1 x2 y1 y2
    [JsonProperty("r")]
    public string round; // round
    [JsonProperty("ch")]
    public List<string> choices { get; set; } // choices
    [JsonProperty("chosen")]
    public string is_trial_chosen; // if choice is made
}
public class PartyMember_c{
    // [JsonProperty("ign")]
    public string ign { get; set; } // text
    public bool is_leader; // visible
    public string area_raw_name { get; set; } // text
    public bool same_location; // visible
    [JsonProperty("sz")]    
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
    [JsonProperty("t")]
    public string text; // text
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    
}

public class AuctionHouseUiCurrencyPickerElements_c{
    [JsonProperty("t")]
    public string text; // text
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("c")]
    public string count; // count
    
}

public class AuctionHouseUiCurrencyPicker_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("c")]
    public List<AuctionHouseUiCurrencyPickerCategory_c> categories { get; set; } // categories
    [JsonProperty("p_e")]
    public List<AuctionHouseUiCurrencyPickerElements_c> presented_elements { get; set; } // presented elements
}

public class AuctionHouseUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // element screen zone x1 x2 y1 y2
    [JsonProperty("i_w_b_sz")]
    public List<int> i_want_button_screen_zone { get; set; } // i want button screen zone x1 x2 y1 y2
    [JsonProperty("i_h_b_sz")]
    public List<int> i_have_button_screen_zone { get; set; } // i have button screen zone x1 x2 y1 y2
    [JsonProperty("g")]
    public string gold_in_inventory; // current gold
    [JsonProperty("o_i_t")]
    public string i_have_item_name; // offered item type
    [JsonProperty("w_i_t")]
    public string i_want_item_name; // wanted item type
    [JsonProperty("dc")]
    public string deal_cost_gold; // deal cost
    [JsonProperty("place_order_b_sz")]
    public List<int> place_order_button_screen_zone { get; set; } // place order button screen zone x1 x2 y1 y2
    [JsonProperty("i_w_f_sz")]
    public List<int> i_want_field_screen_zone { get; set; } // i want field screen zone x1 x2 y1 y2
    [JsonProperty("i_h_f_sz")]
    public List<int> i_have_field_screen_zone { get; set; } // i have field screen zone x1 x2 y1 y2
    [JsonProperty("market_ratios_texts")]
    public List<string> market_ratios_texts;
    [JsonProperty("c_p")]
    public AuctionHouseUiCurrencyPicker_c currency_picker{ get; set; } // currency picker
    [JsonProperty("c_o")]
    public List<AuctionHouseUiOrder_c> current_orders{ get; set; } // current orders
}

public class BlueLine_c{
    [JsonProperty("t")]
    public string text { get; set; } // text
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("v")]
    public int is_visible; // visible
}
public class MapUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("elements")]
    public List<BlueLine_c> text_elements { get; set; } 
}
public class ResurrectUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
}

public class AnointUi_c{
    [JsonProperty("v")]
    public int is_visible; // visible
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("o")]
    public List<InventoryObjectCustom_c> oils { get; set; } // oils
    [JsonProperty("pi")]
    public List<InventoryObjectCustom_c> placed_items { get; set; } // placed items
    [JsonProperty("a_b_sz")]
    public List<int> annoint_button_screen_zone { get; set; } // anoint button zone x1 x2 y1 y2
    [JsonProperty("t")]
    public List<string> texts { get; set; } // texts

}

public class RitualUi_c{
    [JsonProperty("rt_b_v")]
    public int ritual_button_is_visible { get; set; } // ritual button is_visible
    [JsonProperty("rt_b_sz")]
    public List<int> ritual_button_screen_zone { get; set; } // ritual button screen zone
    [JsonProperty("t")]
    public string tribute { get; set; } // tribute
    [JsonProperty("p")]
    public string progress { get; set; } // progress
    [JsonProperty("v")]
    public int purchase_menu_is_visible { get; set; } // is_visible
    [JsonProperty("sz")]
    public List<int> purchase_menu_screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("r_b")]
    public string reroll_button_tooltip_text { get; set; } // reroll button tooltip raw
    [JsonProperty("r_b_sz")]
    public List<int> reroll_button_screen_zone { get; set; } // reroll button screen zone
    [JsonProperty("d_b")]
    public string defer_button_text_raw { get; set; } // defer button text raw
    [JsonProperty("d_b_sz")]
    public List<int> defer_button_screen_zone { get; set; } // defer button screen zone
    [JsonProperty("i")]
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
    [JsonProperty("p")]
    public string path { get; set; } // path
    // [JsonProperty("id")]
    public int id { get; set; } // id it belongs to
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("sz_a")]
    public List<List<int>> screen_zones { get; set; } // array of screen zones label screen zone x1 x2 y1 y2
    [JsonProperty("i_m")]
    public string item_metadata { get; set; } // item_metadata
    // [JsonProperty("p")]
    public List<string> texts { get; set; } // list of texts for this label
    [JsonProperty("v")]
    public int is_visible { get; set; } // is visible
    // [JsonProperty("p_o_s")]
    public Posx1x2y1y2 p_o_s { get; set; } // pos_on_screen
}
public class SkillsOnBar_c
{
    [JsonProperty("c_b_u")]
    public List<int> can_be_used { get; set; } // can_be_used 0 - false 1 - true
    [JsonProperty("cs")]
    public List<int> casts_per_100_seconds { get; set; } // casts per 100 seconds
    [JsonProperty("tu")]
    public List<int> total_uses { get; set; } // total uses
    // below if "full"
    [JsonProperty("i_n")]
    public List<string> internal_name { get; set; } // internal_name
    [JsonProperty("d")]
    public List<List<Dictionary<string, int>>> descriptions { get; set; } // descriptions
}
public class FlasksOnBar
{
    [JsonProperty("n")]
    public List<string> flask_base_names { get; set; } // flask_base_names
    [JsonProperty("cu")]
    public List<int> can_use_flask { get; set; } // can_use_flask
    [JsonProperty("i")]
    public List<int> flask_indexes { get; set; } // index
}
public class PlayerInfo_c
{
    [JsonProperty("gp")]
    public List<int> grid_position { get; set; } // player pos grid position x ,y 
    [JsonProperty("l")]
    public List<int> life_component { get; set; } // life component, [health max,current,reserved, es max,current, reserved, mana max, current, reserved]
    [JsonProperty("b")]
    public List<string> buffs { get; set; } // buffs
    [JsonProperty("db")]
    public List<string> debuffs { get; set; } // debuffs
    [JsonProperty("im")]
    public int is_moving { get; set; } // ismoving
    [JsonProperty("lv")]
    public int lvl { get; set; } // lvl
}
public class MinimapIcon_c
{
    [JsonProperty("i")]
    public int id { get; set; } // id
    [JsonProperty("p")]
    public string path { get; set; } // path
    [JsonProperty("n")]
    public string name { get; set; } // name
    [JsonProperty("v")]
    public int is_visible { get; set; } // is_hide
    [JsonProperty("h")]
    public int is_hidden { get; set; } // is_visible
}


public class Entity_c{
    [JsonProperty("ls")]
    public int[] location_on_screen { get; set; }
    [JsonProperty("p")]
    public string path { get; set; }
    [JsonProperty("r")]
    public string rarity { get; set; }
    [JsonProperty("i")]
    public int id { get; set; }
    [JsonProperty("o")]
    public int is_opened { get; set; }
    [JsonProperty("h")]
    public int is_hostile { get; set; }
    [JsonProperty("ia")]
    public int is_attackable { get; set; }
    [JsonProperty("t")]
    public int is_targetable { get; set; }
    [JsonProperty("it")]
    public int is_targeted { get; set; }
    [JsonProperty("em")]
    public int essenced_mob { get; set; }
    [JsonProperty("b")]
    public int bound_center_pos { get; set; }
    [JsonProperty("gp")]
    public int[] grid_position { get; set; }
    [JsonProperty("wp")]
    public int[] world_position { get; set; }
    [JsonProperty("l")]
    public int[] life_component { get; set; }
    [JsonProperty("rn")]
    public string render_name { get; set; }
    [JsonProperty("et")]
    public string entity_type { get; set; }
    // public string a { get; set; } // animation
}
public class VisibleLabelEntity_c{
    [JsonProperty("ls")]
    public List<int> location_on_screen { get; set; } // location on screen x,y
    [JsonProperty("p")]
    public string path { get; set; } // path
    [JsonProperty("i")]
    public int id { get; set; } // id
    [JsonProperty("t")]
    public int is_targetable { get; set; } // is targetable
    [JsonProperty("b")]
    public int bound_center_pos { get; set; } // BoundsCenterPos
    [JsonProperty("gp")]
    public List<int> grid_position { get; set; } // grid position x, y
    [JsonProperty("wp")]
    public List<int> world_position { get; set; } // world position position x, y, z
    [JsonProperty("rn")]
    public string render_name { get; set; } // render name
    [JsonProperty("et")]
    public string entity_type { get; set; } // entity_type
}
public class ItemOnGroundLabel_c
{
    // [JsonProperty("id")]
    public int id; // id
    [JsonProperty("gp")]
    public int[] grid_position { get; set; } // grid position x ,y 
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    [JsonProperty("a")]
    public string animated_property_metadata; // animated property metadata // itemonground -> components worlditem -> itementity -> components renderitem -> resourcepath
    [JsonProperty("r")]
    public string rarity; // rarity
    [JsonProperty("t")]
    public int is_targetable { get; set; } // is targetable
    [JsonProperty("it")]
    public int is_targeted { get; set; } // is_targeted
    [JsonProperty("dn")]
    public string displayed_name { get; set; } // displayed name
}
public class QuestState_c{
    public string id; // id
    public int state; // id
}
public class GetDataObject
{
    [JsonProperty("br")]
    public int broken_response { get; set; } // broken response
    [JsonProperty("g_s")]
    public int game_state; // game state 0 - broken, 1 - main menu, 10 - select char, 20 - in game
    [JsonProperty("w")]
    public List<int> window_borders { get; set; } // x1 x2 y1 y2
    [JsonProperty("terrain_string")]
    public string terrain_string;
    [JsonProperty("ah")]
    public uint area_hash; // area hash
    [JsonProperty("awake_entities")]
    public List<Entity_c> awake_entities { get; set; }
    [JsonProperty("vl")]
    public List<VisibleLabelEntity_c> visible_labels { get; set; } 
    [JsonProperty("i")]
    public List<ItemOnGroundLabel_c> item_labels { get; set; }
    [JsonProperty("pi")]
    public PlayerInfo_c player_info { get; set; }
    [JsonProperty("ipv")]
    public bool invites_panel_visible { get; set; }
    // [JsonProperty("br")]
    public bool IsLoading { get; set; }
    // [JsonProperty("br")]
    public bool IsLoading_b { get; set; }
    // [JsonProperty("br")]
    public string area_raw_name { get; set; }
    [JsonProperty("f")]
    public FlasksOnBar flasks { get; set; }
    [JsonProperty("s")]
    public SkillsOnBar_c skills { get; set; }
    [JsonProperty("mgp")]
    public List<int> mouse_grid_position { get; set; } // mouse grid pos [x,y]
    [JsonProperty("mcp")]
    public List<int> mouse_cursor_pos { get; set; } // mouse cursor pos [x,y]
    [JsonProperty("c_t")]
    public int controller_type; 
    [JsonProperty("t")]
    public int tick = 0; 
}
public class InventoryObjectCustom_c
{
    // [JsonProperty("br")]
    public string Name { get; set; }
    // [JsonProperty("a")]
    public string a { get; set; } // render_item_component.ResourcePath
    // [JsonProperty("br")]
    public string unique_name { get; set; }
    // [JsonProperty("br")]
    public string rarity { get; set; }
    [JsonProperty("m_t")]
    public int map_tier { get; set; } // map_tier
    [JsonProperty("c")]
    public int is_corrupted { get; set; } // corrupted
    [JsonProperty("i")]
    public int is_identified { get; set; } // identified
    // [JsonProperty("br")]
    public string RenderArt { get; set; }
    // [JsonProperty("br")]
    public int items_in_stack { get; set; }
    // [JsonProperty("br")]
    public List<string> item_mods { get; set; }
    [JsonProperty("imr")]
    public List<string> item_mods_raw { get; set; } // item mods raw
    public List<string> sockets; //TODO their count and runes\soul cores placed
    [JsonProperty("g")]
    public List<int> grid_position { get; set; } // grid pos x1x2y1y2
    [JsonProperty("s")] // rename to sz
    public List<int> screen_zone { get; set; } // screenpos x1x2y1y2
    [JsonProperty("tt")]
    public List<string> tooltip_texts; // tooltip_texts
    // remove below
    public GridPosition_generated TopLeft { get; set; }
    public GridPosition_generated BottomRight { get; set; }
}
public class WorldMapEndGameMapObj
{
    [JsonProperty("sz")]
    public List<int> screen_zone { get; set; } // label screen zone x1 x2 y1 y2
    // [JsonProperty("id")]
    public int id { get; set; }
    // [JsonProperty("tt")]
    public string name { get; set; }
    public string name_raw { get; set; }
    public List<string> icons { get; set; }
    public int can_run { get; set; }
}

public class GetMapDeviceInfoObject
{
    [JsonProperty("ap_o")]   
    public bool atlas_panel_opened { get; set; } // atlas_panel_opened
    [JsonProperty("wm_o")]   
    public bool world_map_opened { get; set; } // world_map_opened
    [JsonProperty("av_m")]   
    public List<WorldMapEndGameMapObj> availiable_maps { get; set; } // avaliable_maps
    [JsonProperty("pmw_o")]   
    public bool place_map_window_is_opened { get; set; } // place_map_window_opened
    [JsonProperty("pmw_sz")]   
    public List<int> place_map_window_screen_zone { get; set; } // place_map_window_screenzone
    [JsonProperty("pmw_t")]   
    public string place_map_window_text { get; set; } // place_map_window_ text
    [JsonProperty("pmw_i")]   
    public List<InventoryObjectCustom_c> placed_items { get; set; } // place_map_window_items
    [JsonProperty("pmw_ab_sz")]   
    public List<int> place_map_window_activate_button_screen_zone { get; set; } // place map window activatte button screenzone
    [JsonProperty("z_b_sz")]   
    public List<int> ziggurat_button_screen_zones { get; set; } // ziggurat button screenzone
    [JsonProperty("rg_sz")]   
    public List<List<int>> realmgate_screenzones { get; set; } // realmgate screenzones
}
public class GetOpenedStashInfoObject
{
    public string status { get; set; } // to remove
    [JsonProperty("IsOpened")]
    public bool is_opened { get; set; }
    [JsonProperty("ls")]
    public List<int> location_on_screen { get; set; } // stash display position location on screen x,y
    [JsonProperty("s_b_p_ls")]
    public List<List<int>> tab_buttons_screen_zones { get; set; } // [ [x1,x2,y1,y2] ] for each stash tab button unsorted, [-1] is the "+"
    // [JsonProperty("IsOpened")]
    public string stash_tab_type { get; set; }
    // [JsonProperty("IsOpened")]
    public int total_stash_tab_count { get; set; }
    public int tab_index { get; set; }
    public List<InventoryObjectCustom_c> items { get; set; }
}
public class GridPosition_generated
{
    public int X { get; set; }
    public int Y { get; set; }
}

