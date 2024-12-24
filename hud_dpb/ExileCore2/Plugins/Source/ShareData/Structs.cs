using System.Collections.Generic;
public struct ShareDataEntity
{
    public string bounds_center_pos;
    public string grid_pos;
    public string pos;
    public string distance_to_player;
    public string on_screen_position;
    public string additional_info;
}

public struct ShareDataContent
{
    public Dictionary<string, ShareDataEntity> items_on_ground_label;
    public ShareDataEntity player_data;
    public string mouse_position;
}

public class Posx1x2y1y2
{
    public int x1 { get; set; }
    public int x2 { get; set; }
    public int y1 { get; set; }
    public int y2 { get; set; }
}

public class KirakMissionUI_c{
    public int v; // visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public List<int> kmv { get; set; } // kirak maps variety[ white yellow red ]
    public List<InventoryObjectCustom_c> items { get; set; } // 
}
public class PurchaseWindowHideout_c{
    public int v; // visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public List<InventoryObjectCustom_c> items { get; set; } // 
}
public class WorldMapUI_c{
    public int v; // visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
}
public class BanditDialogueUi_c{
    public int v; // visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public List<int> k_sz { get; set; } // kill screen zone x1 x2 y1 y2
    public List<int> h_sz { get; set; } // help screen zone x1 x2 y1 y2
}
public class NecropolisPopupUI_c{
    public int v; // visible
    public List<int> eb_sz { get; set; } // enter button screen zone x1 x2 y1 y2
    // public List<int> k_sz { get; set; } // kill screen zone x1 x2 y1 y2
    // public List<int> h_sz { get; set; } // help screen zone x1 x2 y1 y2
}
public class IncursionUiRoom_c{
    public string n; // name
    public int cte; // connected to entrance
    public List<int> sz { get; set; } // screen zone x1 x2 y1 y2

}
public class NpcDialogueUiChoice_c{
    public string t; // text
    public List<int> sz { get; set; } // screen zone x1 x2 y1 y2
}
public class NpcDialogueUi_c{
    public int v; // visible
    public List<NpcDialogueUiChoice_c> ch { get; set; } // choices, possible buttons we can click, [name, screen_zone]
    public List<InventoryObjectCustom_c> rw { get; set; } // rewards choices
    public string nn; // npc_name
    public string t; // text
    public List<int> sz { get; set; } // screen zone x1 x2 y1 y2


}
public class NpcRewardUi_c{
    public int v; // visible
    public List<int> sz { get; set; } // screen zone x1 x2 y1 y2
    public List<InventoryObjectCustom_c> choices { get; set; } // rewards choices

}
public class IncursionUi_c{
    public int v; // visible
    public int eib_v; // enter incursion button visible
    public int tib_v; // take incursion button visible
    public string irt; // incursions remaining text
    public string crn; // current room name
    public List<int> eib_sz { get; set; } // enter incursion button screen zone x1 x2 y1 y2
    public List<string> crc { get; set; } // current room connections raw texts
    public List<string> cruur { get; set; } // current room updates raw texts
    public List<IncursionUiRoom_c> r { get; set; } // rooms
}
public class UltimatumNextWaveUi{
    public int v; // visible
    public int a_b_v; // accept_button is visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public List<int> ch_sz { get; set; } // choices label screen zone x1 x2 y1 y2
    public string r; // round
    public List<string> ch { get; set; } // choices
    public string chosen; // if choice is made

}
public class ResurrectUi_c{
    public int v; // visible
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
}
public class AllUi_c{
    public KirakMissionUI_c km;
    public PurchaseWindowHideout_c pwh;
    public WorldMapUI_c wm;
    public BanditDialogueUi_c bd;
    public NecropolisPopupUI_c np;
    public NpcDialogueUi_c nd;
    public NpcRewardUi_c nr;
    public IncursionUi_c iu;
    public UltimatumNextWaveUi unw;
    public ResurrectUi_c ru;
    public GetOpenedStashInfoObject inv; // inventory
    public GetOpenedStashInfoObject sta; // stash
    public InventoryObjectCustom_c hii; // hovered item info
}
public class VisibleLabel
{
    public string p { get; set; } // path
    public int id { get; set; } // id it belongs to
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public List<List<int>> sz_a { get; set; } // array of screen zones label screen zone x1 x2 y1 y2
    public string i_m { get; set; } // item_metadata
    public List<string> texts { get; set; } // list of texts for this label
    public int v { get; set; } // is visible
    public Posx1x2y1y2 p_o_s { get; set; } // pos_on_screen
}
public class SkillsOnBar_c
{
    public List<int> c_b_u { get; set; } // can_be_used 0 - false 1 - true
    public List<int> cs { get; set; } // casts per 100 seconds
    // below if "full"
    public List<string> i_n { get; set; } // internal_name
    public List<List<Dictionary<string, int>>> d { get; set; } // descriptions
}
public class FlasksOnBar
{
    public List<string> n { get; set; } // flask_base_names
    public List<int> cu { get; set; } // can_use_flask
    public List<int> i { get; set; } // index
}
public class PlayerInfo_c
{
    public List<int> gp { get; set; } // player pos grid position x ,y 
    public List<int> l { get; set; } // life component, [health max,current,reserved, es max,current, reserved, mana max, current, reserved]
    public List<string> b { get; set; } // buffs
    public List<string> db { get; set; } // debuffs
    public int lv { get; set; } // lvl
}
public class MinimapIcon_c
{
    public int i { get; set; } // id
    public string p { get; set; } // path
    public int v { get; set; } // is_hide
    public int h { get; set; } // is_visible
    
}
public class Entity_c{
    public List<int> ls { get; set; } // location on screen x,y
    public string p { get; set; } // path
    public string r { get; set; } // rarirty
    public int i { get; set; } // id
    public int o { get; set; } // is opened
    public int h { get; set; } // is hostile
    public int ia { get; set; } // is_attackable
    public int t { get; set; } // is targetable
    public int it { get; set; } // is_targeted
    public int em { get; set; } // essenced_mob
    public int b { get; set; } // BoundsCenterPos
    public List<int> gp { get; set; } // grid position x, y
    public List<int> wp { get; set; } // world position position x, y, z
    public List<int> l { get; set; } // life component, [health max,current,reserved, es max,current, reserved, mana max, current, reserved]
    public string rn { get; set; } // render name
    public string et { get; set; } // entity_type

}
public class VisibleLabelEntity_c{
    public List<int> ls { get; set; } // location on screen x,y
    public string p { get; set; } // path
    public int i { get; set; } // id
    public int t { get; set; } // is targetable
    public int b { get; set; } // BoundsCenterPos
    public List<int> gp { get; set; } // grid position x, y
    public List<int> wp { get; set; } // world position position x, y, z
    public string rn { get; set; } // render name
    public string et { get; set; } // entity_type
}
public class ItemOnGroundLabel_c
{
    public int id; // id
    public List<int> gp { get; set; } // grid position x ,y 
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public string a; // animated property metadata // itemonground -> components worlditem -> itementity -> components renderitem -> resourcepath
    public List<string> l; // links ['rb', 'gb']
    public string r; // rarity
}
public class QuestState_c{
    public string id; // id
    public int state; // id
}
public class GetDataObject
{
    public int br { get; set; } // broken response
    public int g_s; // game state 0 - broken, 1 - main menu, 10 - select char, 20 - in game
    public List<int> w { get; set; } // window borders x1 x2 y1 y2
    public List<int> mcp { get; set; } // mouse cursor pos [x,y]
    public string terrain_string;
    public uint ah; // area hash
    public List<Entity_c> awake_entities { get; set; }
    public List<VisibleLabelEntity_c> vl { get; set; } // visible labels
    public List<ItemOnGroundLabel_c> i { get; set; } // item_labels
    public PlayerInfo_c pi { get; set; } // player pos grid position x ,y
    public bool ipv { get; set; } // Invites panel visible
    public bool IsLoading { get; set; }
    public bool IsLoading_b { get; set; }
    public string area_raw_name { get; set; }
    public FlasksOnBar f { get; set; }  // flasks
    public SkillsOnBar_c s { get; set; }  // skills
    public List<int> mgp { get; set; } // mouse grid position ingamestate.data.serverdata mouse world pos
}
public class InventoryObjectCustom_c
{
    public string Name { get; set; }
    public string a { get; set; } // render_item_component.ResourcePath
    public string unique_name { get; set; }
    public string rarity { get; set; }
    public string Class { get; set; }
    public string ItemType { get; set; }
    public int m_t { get; set; } // map_tier
    public int c { get; set; } // corrupted
    public int i { get; set; } // identified
    public string RenderArt { get; set; }
    public int items_in_stack { get; set; }
    public List<string> item_mods { get; set; }
    public List<string> imr { get; set; } // item mods raw
    public List<string> l; // links ['rb', 'gb']
    public List<int> g { get; set; } // grid pos x1x2y1y2
    public List<int> s { get; set; } // screenpos x1x2y1y2
    public int ti { get; set; } // tab_index
    public List<string> tt; // tooltip_texts
    public GridPosition_generated LocationTopLeft { get; set; }
    public GridPosition_generated LocationBottomRight { get; set; }
    public GridPosition_generated TopLeft { get; set; }
    public GridPosition_generated BottomRight { get; set; }
}
public class GetInventoryInfoObject
{
    public string status { get; set; }
    public bool IsOpened { get; set; }
    public List<InventoryObjectCustom_c> items { get; set; }
}
public class MapDeviceCraftMod
{
    public Posx1x2y1y2 pos { get; set; }
    public string text { get; set; }
}

public class WorldMapEndGameMapObj
{
    public List<int> sz { get; set; } // label screen zone x1 x2 y1 y2
    public int id { get; set; }
    public string name { get; set; }
    public string name_raw { get; set; }
    public List<string> icons { get; set; }
}

public class GetMapDeviceInfoObject
{
    public bool ap_o { get; set; } // atlas_panel_opened
    public bool wm_o { get; set; } // world_map_opened
    public List<WorldMapEndGameMapObj> av_m { get; set; } // avaliable_maps
    public bool pmw_o { get; set; } // place_map_window_opened
    public List<int> pmw_sz { get; set; } // place_map_window_screenzone
    public List<InventoryObjectCustom_c> pmw_i { get; set; } // place_map_window_items
    public List<int> pmw_ab_sz { get; set; } // place map window activatte button screenzone




    // remove
    public bool IsOpened { get; set; }
    public int slots_count { get; set; }
    public List<int> k_m_c { get; set; } // kirak missions count [ white yellow red]
    public List<string> i_p { get; set; } // invintation_progress [ exarch maven eater]
    public List<List<int>> mc { get; set; } // missions count [einhar[white yellow red] alva[white yellow red] niko[white yellow red] jun[white yellow red]]
    public Posx1x2y1y2 c_m_p { get; set; } // map_device_craft_mod window position
    public List<MapDeviceCraftMod> m_d_c { get; set; } // map_device_craft_mods
    public Posx1x2y1y2 a_b_p { get; set; } // activate_button_pos
    public List<InventoryObjectCustom_c> items { get; set; } // items in map device
}
public class GetOpenedStashInfoObject
{
    public string status { get; set; } // to remove
    public bool IsOpened { get; set; }
    public List<int> ls { get; set; } // stash display position location on screen x,y
    public List<List<int>> s_b_p_ls { get; set; } // [ [x1,x2,y1,y2] ] for each stash tab button unsorted, [-1] is the "+"
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
public class Health_generated{
    public int Total { get; set; }
    public int Current { get; set; }
}
public class Mana_generated
{
    public int Total { get; set; }
    public int Current { get; set; }
}
public class Life_generated
{
    public Health_generated Health { get; set; }
    public Mana_generated Mana { get; set; }
}
public class LocationOnScreen_generated
{
    public int X { get; set; }
    public int Y { get; set; }
}
public class PlayerPos_generated
{
    public int X { get; set; }
    public int Y { get; set; }
}
public class GemToLevelInfo
{
    public LocationOnScreen_generated center_location { get; set; }
    public int width { get; set; }
    public int height { get; set; }
}
