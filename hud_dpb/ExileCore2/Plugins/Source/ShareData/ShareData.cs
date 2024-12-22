using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Net.Sockets;
using System.Collections;
using System.Text.RegularExpressions;
using System.Runtime.InteropServices;

using SharpDX;

using System.Collections.Generic;

using ExileCore2;
using ExileCore2.PoEMemory;
using ExileCore2.PoEMemory.Components;
using ExileCore2.PoEMemory.MemoryObjects;
using ExileCore2.Shared;

using ExileCore2.Shared.Enums;
using ExileCore2.Shared.Helpers;


using GameOffsets2.Native;
using Stack = ExileCore2.PoEMemory.Components.Stack;
using System.Linq;
using System.Threading.Tasks;

namespace ShareData;


public class ShareData : BaseSettingsPlugin<ShareDataSettings>
{

    public Server ServerInstance = null;
    private static bool ServerIsRunning = false;
    private const int DefaultServerPort = 50000;

    public override bool Initialise()
    {
        GameController.LeftPanel.WantUse(() => Settings.Enable);

        int ServerPort = GetServerPort();
        ServerInstance = new Server(ServerPort);
        // https://github.com/IlliumIv/FollowerV2/blob/772c2ab6a6c968dc8e1b44daf842b0d9c0c96f41/FollowerV2.cs as a better way to run a server Task.Run(() => MainRequestingWork());
        // var dataUpdateCoroutine = new Coroutine(DataUpdateEvent(), this);
        // var serverRestartCoroutine = new Coroutine(ServerRestartEvent(), this);
        // Core.ParallelRunner.Run(dataUpdateCoroutine);
        // Core.ParallelRunner.Run(serverRestartCoroutine);

        Task.Run(() => ServerRestartEvent());

        // {
        //     Task.Run(() =>
        //     {
        //         ServerRestartEvent();
        //     });
        // };

        return true;
    }
    private int GetServerPort()
    {
        int Port = DefaultServerPort;
        try
        {
            int ParsedPort = int.Parse(Settings.Port.Value);

            if (1025 <= ParsedPort && ParsedPort < 65535)
            {
                Port = ParsedPort;
            }
        }
        catch (Exception e)
        {
            DebugWindow.LogError($"{nameof(ShareData)} -> {e}, default port is {DefaultServerPort}...");
            Settings.Port.SetValueNoEvent($"{DefaultServerPort}");
        }

        return Port;
    }
    private void RunServer()
    {
        try
        {
            ThreadPool.QueueUserWorkItem(new WaitCallback(ServerInstance.RunServer));
        }
        catch (Exception e) {
            DebugWindow.LogError($"{nameof(ShareData)}. Cant't run server with exception -> {e}");
        }
    }
    public static byte WalkableValue(byte[] data, int bytesPerRow, long c, long r)
    {
        var offset = r * bytesPerRow + c / 2;
        if (offset < 0 || offset >= data.Length)
        {
            throw new Exception(string.Format($"WalkableValue failed: ({c}, {r}) [{bytesPerRow}] => {offset}"));
        }

        byte b;
        if ((c & 1) == 0)
        {
            b = (byte)(data[offset] & 0xF);
        }
        else
        {
            b = (byte)(data[offset] >> 4);
        }
        return b;
    }
    private static StdVector Cast(NativePtrArray nativePtrArray)
    {
        //PepeLa
        //this is going to break one day and everyone's gonna be sorry, but I'm leaving this
        return MemoryMarshal.Cast<NativePtrArray, StdVector>(stackalloc NativePtrArray[] { nativePtrArray })[0];
    }
    public StringBuilder generateMinimap()
    {
        // https://www.ownedcore.com/forums/mmo/path-of-exile/894162-finding-map-data-memory.html
        StringBuilder sb = new StringBuilder();
        int MapCellSizeI = 23;
        var _terrainMetadata = GameController.IngameState.Data.DataStruct.Terrain;
        var MeleeLayerPathfindingData = GameController.Memory.ReadStdVector<byte>(Cast(_terrainMetadata.LayerMelee));

        var BytesPerRow = _terrainMetadata.BytesPerRow;
        var Rows = _terrainMetadata.NumRows;
        var Cols = _terrainMetadata.NumCols;

        for (var r = Rows * MapCellSizeI - 1; r >= 0; --r)
        {
            for (var c = 0; c < Cols * MapCellSizeI; c++)
            {
                var b = WalkableValue(MeleeLayerPathfindingData, BytesPerRow, c, r);
                // var b = 1;
                var ch = b.ToString()[0];
                if (b == 0)
                    ch = '0';
                sb.AppendFormat("{0}", ch);
            }
            sb.AppendLine();
        }
        return sb;
    }
    public List<float> getScreenPos(int grid_x, int grid_y)
    {
        // https://www.ownedcore.com/forums/mmo/path-of-exile/894162-finding-map-data-memory.html
        List<float> coords = new List<float>();
        // Core.States.InGameStateObject.CurrentAreaInstance.Player.TryGetComponent<Render>(out var r);
        var height = GameController.EntityListWrapper.Player.Pos.Z;//r.TerrainHeight
        try
        {
            height = GameController.IngameState.Data.RawTerrainHeightData[(int)grid_y][(int)grid_x];
            // height = -height;
            // height = IngameData.RawTerrainHeightData[(int)grid_y][(int)grid_x];
            // height = Core.States.InGameStateObject.CurrentAreaInstance.GridHeightData[(int)grid_y][(int)grid_x];
        }
        catch (Exception)
        {
        }

        const int TileToGridConversion = 23;
        const int TileToWorldConversion = 250;
        const float GridToWorldMultiplier = TileToWorldConversion / (float)TileToGridConversion;


        var screenCoord = GameController.IngameState.Camera.WorldToScreen(
            new System.Numerics.Vector3(
                grid_x * GridToWorldMultiplier, 
                grid_y * GridToWorldMultiplier, 
                height
            )
        );
        var x = screenCoord.X;
        var y = screenCoord.Y;
        coords.Add(x);
        coords.Add(y);
        return coords;

    }
    public string serializeEntityType(string entity_type){
        string return_val = entity_type;
        if (entity_type == "Monster"){
            return_val = "m";
        } else if (entity_type == "AreaTransition"){
            return_val = "at";
        } else if (entity_type == "Chest"){
            return_val = "c";
        } else if (entity_type == "WorldItem"){
            return_val = "wi";
        } else if (entity_type == "Chest"){
            return_val = "c";
        } else if (entity_type == "Chest"){
            return_val = "c";
        }
        return return_val;
    }
    public List<Entity_c> getAwakeEntities(){
        List<Entity_c> awake_entities = new List<Entity_c>();
        foreach (var obj in GameController.EntityListWrapper.Entities)
        {
            // ignore invalid or temp objects
            if (obj.IsValid != true){
                continue;
            }
            
            // ignore effect objects
            if (obj.Type == EntityType.Effect){
                continue;
            }

            Entity_c entity = new Entity_c();
            entity.i = (int)obj.Id;
            entity.p = obj.Path;
            entity.gp = new List<int> { (int)obj.GridPos.X, (int)obj.GridPos.Y };
            entity.wp = new List<int> { (int)obj.BoundsCenterPos.X,(int)obj.BoundsCenterPos.Y,(int)obj.BoundsCenterPos.Z };
            // life component if it has it
            try
            {
                var obj_life = obj.GetComponent<Life>();
                // Life_generated life_component = new Life_generated();
                // life_component.Health = new Health_generated();
                // life_component.Mana = new Mana_generated();

                // life_component.Health.Total = obj_life.MaxHP;
                // life_component.Health.Current = obj_life.CurHP;

                // life_component.Mana.Total = obj_life.MaxMana;
                // life_component.Mana.Current = obj_life.CurMana;

                // entity.life = life_component;
                entity.l = new List<int> { 
                    obj_life.MaxHP,
                    obj_life.CurHP,
                    obj_life.Health.Reserved,
                    obj_life.MaxMana,
                    obj_life.CurMana,
                    obj_life.Mana.Reserved,
                    obj_life.MaxES,
                    obj_life.CurES,
                    obj_life.EnergyShield.Reserved,
                };
            }
            catch (Exception e)
            {
                
            }

            // entity_type
            entity.et = serializeEntityType(obj.Type.ToString());

            // BoundsCenterPos
            // need for checking if item is collectable
            try {
                if ((int)obj.BoundsCenterPos.X != 0){
                    entity.b = 1;
                } else {
                    entity.b = 0;
                }
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities BoundsCenterPos -> {e}");
                
            } 

            // loc on screen
            try {
                int loc_on_screen_x = 0;
                int loc_on_screen_y = 0;

                if ((int)obj.BoundsCenterPos.X != 0){
                    var loc_on_screen = GameController.IngameState.Camera.WorldToScreen(obj.BoundsCenterPos);
                    loc_on_screen_x = (int)loc_on_screen.X;
                    loc_on_screen_y = (int)loc_on_screen.Y;
                } else if (entity.et == "wi") {
                    continue;
                }

                entity.ls = new List<int> { loc_on_screen_x, loc_on_screen_y };
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities -> {e}");
                
            }



            // render name # need only for area transitions
            entity.rn = obj.RenderName;

            // Rarity
            try {
                entity.r = obj.Rarity.ToString();

            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities -> {e}");
                
            } 

            // IsHostile
            try {
                entity.h = obj.IsHostile ? 1 : 0;

            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities -> {e}");
                
            } 


            // is_attackable
            if ( 
                !obj.HasComponent<Monster>() ||
                !obj.HasComponent<Positioned>() ||
                !obj.HasComponent<Render>() ||
                !obj.TryGetComponent<Buffs>(out var buffs) ||
                buffs.HasBuff("hidden_monster") || // legion
                buffs.HasBuff("hidden_monster_disable_minions") || // essences
                !obj.IsHostile ||
                !obj.HasComponent<Life>() ||
                !obj.IsAlive ||
                !obj.HasComponent<ObjectMagicProperties>()
            ) {
                entity.ia = 0;
            } else {
                entity.ia = 1;
            }

            // essenced_mob
            entity.em = 0;
            if (entity.ia == 1) {
                var magic_properties = obj.GetComponent<ObjectMagicProperties>();
                if (magic_properties != null){
                    if (magic_properties.Rarity == MonsterRarity.Rare){
                        foreach (var mod_str in magic_properties.Mods){
                            if (mod_str.Contains("EssenceDaemon") == true){
                                entity.em = 1;
                                break;
                            }
                        }
                    }
                }
            }


            // is_opened
            entity.o = 0;
            try {
                entity.o = obj.IsOpened ? 1 : 0;
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"entity.IsOpened -> {e}");
                
            }
            
            var triggerable_blockage = obj.GetComponent<TriggerableBlockage>();
            if (triggerable_blockage != null){
                entity.o = triggerable_blockage.IsOpened ? 1 : 0;
            }


            // is_targetable
            try {
                entity.t = obj.IsTargetable ? 1 : 0;
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"Targetable -> {e}");
            }


            // // AnimatedPropertiesMetadata
            // var animated_metadata = obj.GetComponent<Animated>();
            // if (animated_metadata != null){
            //     entity.a = animated_metadata.BaseAnimatedObjectEntity.Metadata;
            // }

            awake_entities.Add(entity);
        }
        return awake_entities;
    }
    string SendResponse(HttpListenerRequest request){
        DebugWindow.LogMsg($"got request {request.RawUrl}");

        if (request.Url.AbsolutePath == "/getData"){
            var request_type = "partial";
            try{
                request_type = request.RawUrl.Split(new [] { "type=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0];
                request_type = "full";
            } catch (Exception ex){}
            DebugWindow.LogMsg(request_type);
            var response = getData(request_type);
            DebugWindow.LogMsg("sending response");
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath == "/getLocationOnScreen"){
            int x = int.Parse(request.RawUrl.Split(new [] { "x=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
            int y = int.Parse(request.RawUrl.Split(new [] { "y=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
            int z = int.Parse(request.RawUrl.Split(new [] { "z=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
            var screenCoord = GameController.IngameState.Camera.WorldToScreen(new System.Numerics.Vector3(x,y,z));
            // var screenCoord = GameController.IngameState.Camera.WorldToScreen(new Vector3(x,y,z));
            var coords = new List<int> {
                (int)screenCoord.X,
                (int)screenCoord.Y
            };
            return Newtonsoft.Json.JsonConvert.SerializeObject(coords);
        
        } else if (request.Url.AbsolutePath == "/getScreenPos"){
            int y = int.Parse(request.RawUrl.Split(new [] { "y=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
            int x = int.Parse(request.RawUrl.Split(new [] { "x=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
            var pos = getScreenPos(x, y);
            return Newtonsoft.Json.JsonConvert.SerializeObject(pos);
        } else if (request.Url.AbsolutePath == "/getInventoryInfo"){
            var response = getInventoryInfo();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath == "/getOpenedStashInfo"){
            var response = getStashInfo();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/gemsToLevel"){
            List<GemToLevelInfo> response = getGemsToLevelInfo();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getVisibleLabelOnGroundEntities"){
            var response = getVisibleLabelOnGroundEntities();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath =="/getItemsOnGroundLabelsVisible"){
            List<ItemOnGroundLabel_c> response = getItemsOnGroundLabelsVisible();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath =="/mapDeviceInfo"){
            GetMapDeviceInfoObject response = mapDeviceInfo();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getAtlasProgress"){
            List<string> response = getAtlasProgress();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getVisibleLabels"){
            List<VisibleLabel> response = getVisibleLabels();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath =="/getHoveredItemInfo"){
            InventoryObjectCustom_c response = getHoveredItemInfo();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath =="/getSkillBar"){
            SkillsOnBar_c response = getSkillBar(true);
            return Newtonsoft.Json.JsonConvert.SerializeObject(response);
        } else if (request.Url.AbsolutePath =="/getLabTrialsState"){
            var response = GameController.IngameState.IngameUi.GetQuests;
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getQuestStates"){
            var response = getQuestStates();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getWaypointsState"){
            var response = GameController.IngameState.Data.ServerData.WaypointsUnlockState;
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getMinimapIcons"){
            var response = getMinimapIcons();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getWorldMapUi"){
            var response = getWorldMapUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getUltimatumNextWaveUi"){
            var response = getUltimatumNextWaveUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getResurrectUi"){
            var response = getResurrectUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        }  else if (request.Url.AbsolutePath =="/getPurchaseWindowHideoutUi"){
            var response = getPurchaseWindowHideoutUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getKirakMissionsUi"){
            var response = getKirakMissionsUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getQuestFlags"){
            var response = GameController.IngameState.Data.ServerData.QuestFlags;
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getPreloadedFiles"){
            var response = getPreloadedFiles();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getBanditDialogueUi"){
            var response = getBanditDialogueUi();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/ForceRefreshArea"){
            GameController.Area.ForceRefreshArea();
            var response = "ForceRefreshArea_OK";
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getNecropolisPopupUI"){
            var response = getNecropolisPopupUI();
            return Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
        } else if (request.Url.AbsolutePath =="/getIncursionUi"){
            try{
                var response = getIncursionUi();
                return Newtonsoft.Json.JsonConvert.SerializeObject(response);
            } catch (Exception ex){
                DebugWindow.LogMsg($"response getIncursionUi {ex}");
            }
        } else if (request.Url.AbsolutePath =="/getNpcDialogueUi"){
            try{
                var response = getNpcDialogueUi();
                return Newtonsoft.Json.JsonConvert.SerializeObject(response);
            } catch (Exception ex){
                DebugWindow.LogMsg($"response geNpcDialogueUi {ex}");
            }
        } else if (request.Url.AbsolutePath =="/getNpcRewardUi"){
            try{
                var response = getNpcRewardUi();
                return Newtonsoft.Json.JsonConvert.SerializeObject(response);
            } catch (Exception ex){
                DebugWindow.LogMsg($"response getNpcRewardUi {ex}");
            }
        } else {
            return "dont understand";
        };
        return "dont understand";
    }
    public InventoryObjectCustom_c getHoveredItemInfo(){
        InventoryObjectCustom_c hovered_item = new InventoryObjectCustom_c();
        var hovered_item_el = GameController.IngameState.UIHoverElement;
        var tooltip_texts_el = hovered_item_el.Tooltip;
        if (tooltip_texts_el != null){
            hovered_item.tt = new List<string>(); 
            foreach (var text_line in tooltip_texts_el.Children[0].Children[1].Children){
                if (text_line.TextNoTags != null){
                    hovered_item.tt.Add(text_line.TextNoTags);
                }
            }
        }
        return hovered_item;
    }

    public GetOpenedStashInfoObject getStashInfo(){
        GetOpenedStashInfoObject response = new GetOpenedStashInfoObject();
        response.status = "closed";
        var stash_visible = GameController.IngameState.IngameUi.StashElement.IsVisible;
        if (stash_visible == true){
            var stash_tab_index = GameController.IngameState.IngameUi.StashElement.IndexVisibleStash;
            response.tab_index = stash_tab_index;
            response.total_stash_tab_count = (int)GameController.IngameState.IngameUi.StashElement.TotalStashes;
            response.stash_tab_type = GameController.IngameState.IngameUi.StashElement.AllInventories[stash_tab_index].InvType.ToString();
            List<InventoryObjectCustom_c> items = new List<InventoryObjectCustom_c>();

            response.s_b_p_ls = new List<List<int>>();
            foreach (var switch_el in GameController.IngameState.IngameUi.StashElement.Children[2].Children[0].Children[0].Children[1].Children[0].Children){
                // broken one?
                if (switch_el.ChildCount == 0){
                    continue;
                }
                var element_rect = switch_el.GetClientRect(); // label_element_rect
                var x1x2y1y2 = new List<int> {
                    (int)element_rect.X, 
                    (int)(element_rect.X + element_rect.Width), 
                    (int)element_rect.Y, 
                    (int)(element_rect.Y + element_rect.Height), 
                };
                response.s_b_p_ls.Add(x1x2y1y2);

            }
            foreach (var normal_inventory_item in GameController.IngameState.IngameUi.StashElement.AllInventories[stash_tab_index].VisibleInventoryItems){
                try{
                    var item = normal_inventory_item.Item;
                    if (item == null){
                        continue;
                    }
                    InventoryObjectCustom_c generated_inventory_object = convertItem(item);

                    GridPosition_generated BottomRight = new GridPosition_generated();
                    GridPosition_generated TopLeft = new GridPosition_generated();
                    TopLeft.X = (int)normal_inventory_item.GetClientRect().TopLeft.X;
                    TopLeft.Y = (int)normal_inventory_item.GetClientRect().TopLeft.Y;
                    BottomRight.X = (int)normal_inventory_item.GetClientRect().BottomRight.X;
                    BottomRight.Y = (int)normal_inventory_item.GetClientRect().BottomRight.Y;
                    generated_inventory_object.BottomRight = BottomRight;
                    generated_inventory_object.TopLeft = TopLeft;
                    items.Add(generated_inventory_object);
                } catch (Exception e){
                    DebugWindow.LogMsg($"getOpenedStashInfo normal_inventory_item -> {e}");
                }


            }
            response.items = items;

            
            response.status = "opened";
        }
        return response;
    }

    public GetOpenedStashInfoObject getInventoryInfo(){
        GetOpenedStashInfoObject inventory_info = new GetOpenedStashInfoObject();
        var inventory_panel_element = GameController.IngameState.IngameUi.InventoryPanel;
        inventory_info.IsOpened = inventory_panel_element.IsVisible;
        if ( inventory_panel_element.Address == 0){
            inventory_info.IsOpened = false;
        }
        
        List<InventoryObjectCustom_c> items = new List<InventoryObjectCustom_c>();
        foreach (var normal_inventory_item in GameController.IngameState.Data.ServerData.PlayerInventories[0].Inventory.InventorySlotItems){
            var item = normal_inventory_item.Item;
            InventoryObjectCustom_c generated_inventory_object = convertItem(item);
            var el_rect = normal_inventory_item.GetClientRect();
            // screen_zone
            generated_inventory_object.s = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };
            // grid_position
            generated_inventory_object.g = new List<int> {
                (int)normal_inventory_item.PosX, 
                (int)(normal_inventory_item.PosX + normal_inventory_item.SizeX), 
                (int)normal_inventory_item.PosY, 
                (int)(normal_inventory_item.PosY + normal_inventory_item.SizeY), 
            };
            items.Add(generated_inventory_object);
            
        }
        inventory_info.items = items;
        return inventory_info;
    }
    public KirakMissionUI_c getKirakMissionsUi(){
        KirakMissionUI_c el = new KirakMissionUI_c();
        var ui_element = GameController.IngameState.IngameUi.ZanaMissionChoice;
        el.v = ui_element.IsVisible ? 1 : 0;
        if (el.v == 0){
            return el;
        }
        var el_rect = ui_element.GetClientRect(); // label_element_rect
        el.sz = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        el.kmv = new List<int>();
        el.items = new List<InventoryObjectCustom_c>();

        var items_in_missions = GameController.IngameState.Data.ServerData.NPCInventories[0];
        var ui_elements_in_missions = ui_element.Children[0].Children[3].Children;
        int prev_counter = 0;
        int counter = 0;
        int tab_index = 0;
        // ju min
        var maps_header = ui_element.Children[0].Children[0];
        foreach( var tab in maps_header.Children){
            var count = int.Parse(tab.Children[0].Text);
            el.kmv.Add(count);
            counter += count;
            foreach (var normal_inventory_item in items_in_missions.Inventory.InventorySlotItems){
                var item = normal_inventory_item.Item;
                if (item == null){
                    continue;
                }
                var item_index = normal_inventory_item.PosX; 
                if (item_index >= counter || item_index < prev_counter){
                    continue;
                }

                InventoryObjectCustom_c generated_inventory_object = convertItem(item);
                var item_rect = ui_elements_in_missions[item_index].GetClientRect();
                generated_inventory_object.s = new List<int> {
                    (int)item_rect.X, 
                    (int)(item_rect.X + item_rect.Width), 
                    (int)item_rect.Y, 
                    (int)(item_rect.Y + item_rect.Height), 
                };

                generated_inventory_object.g = new List<int> {
                    normal_inventory_item.PosX,
                    normal_inventory_item.PosY,
                    normal_inventory_item.PosX + normal_inventory_item.SizeX,
                    normal_inventory_item.PosY + normal_inventory_item.SizeY
                };

                generated_inventory_object.ti = tab_index;
                el.items.Add(generated_inventory_object);
            }
            tab_index += 1;
            prev_counter += count;

        }

        // var items_in_missions = GameController.IngameState.Data.ServerData.NPCInventories[0][::];
        // items_in_missions.InventorySlotItems.sort(el=>el.PosX);
        // items_in_missions.map(el=>{

        // });


        return el;
    }
    public PurchaseWindowHideout_c getPurchaseWindowHideoutUi(){
        PurchaseWindowHideout_c el = new();
        var ui_element = GameController.IngameState.IngameUi.PurchaseWindowHideout;
        el.v = ui_element.IsVisible ? 1 : 0;
        if (el.v == 0){
            return el;
        }
        var el_rect = ui_element.GetClientRect(); // label_element_rect
        el.sz = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        el.items = new List<InventoryObjectCustom_c>();
        var tab_container = ui_element.TabContainer;

        foreach (var normal_inventory_item in tab_container.VisibleStash.VisibleInventoryItems){
            try{
                var item = normal_inventory_item.Item;
                if (item == null){
                    continue;
                }
                InventoryObjectCustom_c generated_inventory_object = convertItem(item);

                var item_rect = normal_inventory_item.GetClientRect();
                generated_inventory_object.s = new List<int> {
                    (int)item_rect.X, 
                    (int)(item_rect.X + item_rect.Width), 
                    (int)item_rect.Y, 
                    (int)(item_rect.Y + item_rect.Height), 
                };
                el.items.Add(generated_inventory_object);
            } catch (Exception e){
                DebugWindow.LogMsg($"getPurchaseWindowHideoutUi normal_inventory_item -> {e}");
            }
        }

        return el;
    }
    public List<MinimapIcon_c> getMinimapIcons(){
        List<MinimapIcon_c> awake_entities = new List<MinimapIcon_c>();
        foreach (var obj in GameController.EntityListWrapper.Entities)
        {
            // ignore invalid or temp objects
            if (obj.IsValid != true){
                continue;
            }
            MinimapIcon_c entity = new MinimapIcon_c();
            // Minimap icon
            var minimap_object_component = obj.GetComponent<MinimapIcon>();
            if (minimap_object_component != null){
                entity.h = minimap_object_component.IsHide ? 1 : 0;
                entity.v = minimap_object_component.IsVisible ? 1 : 0;
            } else {
                continue;
            }
            entity.i = (int)obj.Id;
            entity.p = obj.Path;


            awake_entities.Add(entity);
        }
        return awake_entities;
    }
    public BanditDialogueUi_c getBanditDialogueUi(){
        BanditDialogueUi_c el = new BanditDialogueUi_c();
        el.v = GameController.IngameState.IngameUi.BanditDialog.IsVisible ? 1 : 0;
        var el_rect = GameController.IngameState.IngameUi.BanditDialog.GetClientRect(); // label_element_rect
        el.sz = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        if (el.v == 1){
            var help_button_rect = GameController.IngameState.IngameUi.BanditDialog.HelpButton.GetClientRect(); // label_element_rect
            el.h_sz =new List<int> {
                (int)help_button_rect.X, 
                (int)(help_button_rect.X + help_button_rect.Width), 
                (int)help_button_rect.Y, 
                (int)(help_button_rect.Y + help_button_rect.Height), 
            };
            var kill_button_rect = GameController.IngameState.IngameUi.BanditDialog.KillButton.GetClientRect(); // label_element_rect
            el.k_sz = new List<int> {
                (int)kill_button_rect.X, 
                (int)(kill_button_rect.X + kill_button_rect.Width), 
                (int)kill_button_rect.Y, 
                (int)(kill_button_rect.Y + kill_button_rect.Height), 
            };
        }
        return el;
    }
    public NecropolisPopupUI_c getNecropolisPopupUI(){
        NecropolisPopupUI_c el = new NecropolisPopupUI_c();
        var necropolis_popup_element = GameController.IngameState.IngameUi.NecropolisMonsterPanel;
        el.v = necropolis_popup_element.IsVisible ? 1 : 0;
        if (el.v == 1){
            var enter_button_rect = necropolis_popup_element.Children[3].Children[2].Children[0].GetClientRect(); // label_element_rect
            el.eb_sz =new List<int> {
                (int)enter_button_rect.X, 
                (int)(enter_button_rect.X + enter_button_rect.Width), 
                (int)enter_button_rect.Y, 
                (int)(enter_button_rect.Y + enter_button_rect.Height), 
            };

        }
        return el;
    }
    public IncursionUi_c getIncursionUi(){
        IncursionUi_c el = new IncursionUi_c();
        var incursion_element = GameController.IngameState.IngameUi.IncursionWindow;
        el.v = incursion_element.IsVisible ? 1 : 0;
        if (el.v == 1){
            el.eib_v = incursion_element.AcceptElement.IsVisible ? 1 : 0;
            el.tib_v = incursion_element.Children[7].IsVisible ? 1 : 0;
            

            el.irt = incursion_element.Children[5].Text;
            el.crn = incursion_element.Children[3].Children[13].Children[1].Text;
            el.cruur = new List<string> {
                incursion_element.Reward1,
                incursion_element.Reward2
            };

            var enter_incursion_button_element_rect = incursion_element.AcceptElement.GetClientRect();
            el.eib_sz = new List<int> {
                (int)enter_incursion_button_element_rect.X, 
                (int)(enter_incursion_button_element_rect.X + enter_incursion_button_element_rect.Width), 
                (int)enter_incursion_button_element_rect.Y, 
                (int)(enter_incursion_button_element_rect.Y + enter_incursion_button_element_rect.Height), 
            };

            var current_room_connections = new List<string>();
            var current_rooms_element = incursion_element.Children[3].Children[13].Children[0];
            for (int i = 3; i < 9; i++){
                var room_element = current_rooms_element.Children[i];
                var room_element_text = room_element.Children[1].Tooltip.Text;
                current_room_connections.Add(room_element_text);
            }
            el.crc = current_room_connections;


            var rooms = new List<IncursionUiRoom_c>();
            var rooms_element = incursion_element.Children[3];
            for (int i = 0; i < 13; i++){
                IncursionUiRoom_c room = new IncursionUiRoom_c(); 
                var room_element = rooms_element.Children[i];
                room.n = room_element.Children[0].Children[0].Text;
                var room_element_rect = room_element.GetClientRect();
                room.sz =new List<int> {
                    (int)room_element_rect.X, 
                    (int)(room_element_rect.X + room_element_rect.Width), 
                    (int)room_element_rect.Y, 
                    (int)(room_element_rect.Y + room_element_rect.Height), 
                };
                rooms.Add(room);
            }
            el.r = rooms;
        }
        return el;
    }
    public NpcDialogueUi_c getNpcDialogueUi(){
        NpcDialogueUi_c el = new NpcDialogueUi_c();
        el.v = 1;
        el.ch = new List<NpcDialogueUiChoice_c>();
        var elements_to_iterate = new List<Element>();
        if (GameController.IngameState.IngameUi.ExpeditionNpcDialog.IsVisible == true){
            var el_rect = GameController.IngameState.IngameUi.ExpeditionNpcDialog.GetClientRect();
            el.sz = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };
            var dialog_el = GameController.IngameState.IngameUi.ExpeditionNpcDialog.Children[1];
            if (dialog_el.Children[2].IsVisible == true){ // if its a text
                dialog_el = dialog_el.Children[2].Children[0].Children[2].Children[0].Children[0];
                el.t = dialog_el.TextNoTags;
            } else { // if its a dialogue with choices
                // 1 2
                foreach (var choice_element in dialog_el.Children[1].Children[2].Children){
                    elements_to_iterate.Add(choice_element);
                }
                // 0 0 2 
                foreach (var choice_element in dialog_el.Children[0].Children[0].Children[2].Children){
                    elements_to_iterate.Add(choice_element);
                }
                // 0 2 2
                foreach (var choice_element in dialog_el.Children[0].Children[2].Children[2].Children){
                    elements_to_iterate.Add(choice_element);
                }
            }
        } else if (GameController.IngameState.IngameUi.NpcDialog.IsVisible == true) {
            var el_rect = GameController.IngameState.IngameUi.NpcDialog.GetClientRect();
            el.sz = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };

            if (GameController.IngameState.IngameUi.NpcDialog.NpcLineWrapper.ChildCount != 0){
                foreach (var choice_element in GameController.IngameState.IngameUi.NpcDialog.NpcLineWrapper.Children){
                    elements_to_iterate.Add(choice_element);
                }
            } else {
                // 1 2 0 0 2 .TextNoTags
                el.t = GameController.IngameState.IngameUi.NpcDialog.GetChildAtIndex(1)?.GetChildAtIndex(2)?.GetChildAtIndex(0)?.GetChildAtIndex(0)?.GetChildAtIndex(2)?.TextNoTags;
            }
            var dialog_el = GameController.IngameState.IngameUi.NpcDialog.Children[0];
        } else {
            var reward_ui = getNpcRewardUi();
            if (reward_ui.v != 0){
                el.sz = reward_ui.sz;
                el.rw = reward_ui.choices;
            } else {
                el.v = 0;
            }
        }
        if (elements_to_iterate.Count != 0){
            foreach (var choice_element in elements_to_iterate){
                if (choice_element.ChildCount != 0){
                    NpcDialogueUiChoice_c npc_dialogue_choice = new NpcDialogueUiChoice_c();
                    npc_dialogue_choice.t = choice_element.Children[0].TextNoTags;
                    var el_rect = choice_element.GetClientRect();
                    npc_dialogue_choice.sz = new List<int> {
                        (int)el_rect.X, 
                        (int)(el_rect.X + el_rect.Width), 
                        (int)el_rect.Y, 
                        (int)(el_rect.Y + el_rect.Height), 
                    };
                    el.ch.Add(npc_dialogue_choice);
                }
            }
        }

        return el;
    }
    public NpcRewardUi_c getNpcRewardUi(){
        NpcRewardUi_c el = new NpcRewardUi_c();
        el.choices = new List<InventoryObjectCustom_c>();
        el.v = GameController.IngameState.IngameUi.QuestRewardWindow.IsVisible ? 1 : 0;
        if (el.v != 0){
            var el_rect = GameController.IngameState.IngameUi.QuestRewardWindow.GetClientRect(); // label_element_rect
            el.sz = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };
            var rewards_list_element = GameController.IngameState.IngameUi.QuestRewardWindow.Children[5].Children[0].Children[0];
            foreach (var reward in rewards_list_element.Children){
                var reward_element = reward.Children[0].Children[1];
                var item = convertItem(reward_element.Entity);
                var item_rect = reward_element.GetClientRect(); 
                item.s = new List<int> {
                    (int)item_rect.X, 
                    (int)(item_rect.X + item_rect.Width), 
                    (int)item_rect.Y, 
                    (int)(item_rect.Y + item_rect.Height), 
                };
                el.choices.Add(item);
            }
        }
        return el;
    }
    public WorldMapUI_c getWorldMapUi(){
        WorldMapUI_c el = new WorldMapUI_c();
        el.v = GameController.IngameState.IngameUi.WorldMap.IsVisible ? 1 : 0;
        var el_rect = GameController.IngameState.IngameUi.WorldMap.GetClientRect(); // label_element_rect
        el.sz = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        return el;
    }
    public UltimatumNextWaveUi getUltimatumNextWaveUi(){
        UltimatumNextWaveUi el = new UltimatumNextWaveUi();
        var ultimatum_next_wave_ui_element = GameController.IngameState.IngameUi.Root.Children[1].Children[99];
        el.v = ultimatum_next_wave_ui_element.IsVisible ? 1 : 0;
        if (el.v == 1){
            try {
                var el_rect = ultimatum_next_wave_ui_element.GetClientRect(); // label_element_rect
                el.sz = new List<int> {
                    (int)el_rect.X, 
                    (int)(el_rect.X + el_rect.Width), 
                    (int)el_rect.Y, 
                    (int)(el_rect.Y + el_rect.Height), 
                };
                var round_text = ultimatum_next_wave_ui_element.Children[0].Children[3].Text;
                el.r = round_text;
                // ultimatum choices
                el.ch = new List<string>();
                var ultimatum_choices = ultimatum_next_wave_ui_element.Children[2].Children[4].Children[0].Children;
                foreach (var child_element in ultimatum_choices){
                    var text = "???";
                    try {
                        var child_element_nested = child_element.Tooltip.Children[1].Children[3]; 
                        text = child_element_nested.Text;
                    }  catch (Exception ex){
                        DebugWindow.LogMsg($"getvisible lables ultimatum next window choices {ex}");
                    }
                    el.ch.Add(text);
                }
                var ch_el_rect = ultimatum_next_wave_ui_element.Children[2].Children[4].Children[0].GetClientRect(); // label_element_rect
                el.ch_sz = new List<int> {
                    (int)ch_el_rect.X, 
                    (int)(ch_el_rect.X + ch_el_rect.Width), 
                    (int)ch_el_rect.Y, 
                    (int)(ch_el_rect.Y + ch_el_rect.Height), 
                };
                var visible_text = ultimatum_next_wave_ui_element.Children[2].Children[6].Children[0].Children[1].IsVisible ? "visible" : "not_visible" ;
                el.chosen = visible_text;

            }  catch (Exception ex){
                DebugWindow.LogMsg($"getUltimatumNextWaveUi {ex}");
            }
        }
        return el;
    }
    public ResurrectUi_c getResurrectUi(){
        ResurrectUi_c el = new ResurrectUi_c();
        el.v = GameController.IngameState.IngameUi.ResurrectPanel.IsVisible ? 1 : 0;
        var el_rect = GameController.IngameState.IngameUi.ResurrectPanel.GetClientRect(); // label_element_rect
        el.sz = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        return el;
    }
    public List<string> getAtlasProgress(){
        // returns list of strings of completed maps
        List<string> finished_maps = new List<string>();
        // foreach (var finished_map in GameController.IngameState.Data.ServerData.BonusCompletedAreas){
        //     finished_maps.Add(finished_map.Name);
        // }
        return finished_maps;
    }
    public List<QuestState_c> getQuestStates(){
        List<QuestState_c> quest_states = new List<QuestState_c>();
        // var updated_quest_states = GameController.IngameState.IngameUi.GenerateQuestStates();
        var updated_quest_states = GameController.IngameState.IngameUi.GetQuests;
        DebugWindow.LogMsg("updated_quest_states type is: ");
        // DebugWindow.LogMsg(updated_quest_states.GetType());
        DebugWindow.LogMsg(updated_quest_states.GetType().ToString());

        foreach (var quest_state in updated_quest_states){
            DebugWindow.LogMsg("quest_state type is: ");
            DebugWindow.LogMsg(quest_state.GetType().ToString());
            QuestState_c q_s = new QuestState_c();
            q_s.id = quest_state.Item1.Id;
            q_s.state = quest_state.Item2;
            quest_states.Add(q_s);
        }
        return quest_states;
    }
    public List<ItemOnGroundLabel_c> getItemsOnGroundLabelsVisible(){
        List<ItemOnGroundLabel_c> visible_labels = new List<ItemOnGroundLabel_c>();
        foreach (var label in GameController.IngameState.IngameUi.ItemsOnGroundLabelElement.LabelsOnGroundVisible){

            if (label.ItemOnGround.Path != "Metadata/MiscellaneousObjects/WorldItem") {
                continue;
            }
            ItemOnGroundLabel_c visible_label = new ItemOnGroundLabel_c();
            // id
            visible_label.id = (int)label.ItemOnGround.Id;
            
            // grid position
            visible_label.gp = new List<int> {
                (int)label.ItemOnGround.GridPos.X,
                (int)label.ItemOnGround.GridPos.Y
            };
            var label_element = label.Label; 
            // screen zone
            var label_element_rect = label_element.GetClientRect(); // label_element_rect
            visible_label.sz = new List<int> {
                (int)label_element_rect.X, 
                (int)(label_element_rect.X + label_element_rect.Width), 
                (int)label_element_rect.Y, 
                (int)(label_element_rect.Y + label_element_rect.Height), 
            };

            var world_item_component = label.ItemOnGround.GetComponent<WorldItem>();
            if (world_item_component != null){
                var item_entity = world_item_component.ItemEntity;
                // icon?
                var render_item_component = item_entity.GetComponent<RenderItem>();
                if (render_item_component != null){
                    visible_label.a = render_item_component.ResourcePath;
                }
                // sockets
                var sockets_component = item_entity.GetComponent<Sockets>();
                if (sockets_component != null){
                    visible_label.l = sockets_component.SocketGroup;
                }
                // mods
                var mods_component = item_entity.GetComponent<Mods>();
                if (mods_component != null){
                    visible_label.r = mods_component.ItemRarity.ToString();
                }
            }
            
            
            
            visible_labels.Add(visible_label);

        }

        return visible_labels;

    }
    public List<VisibleLabel> getVisibleLabels(){
        List<VisibleLabel> visible_labels = new List<VisibleLabel>();
        foreach (var label in GameController.IngameState.IngameUi.ItemsOnGroundLabelElement.LabelsOnGroundVisible){
            VisibleLabel visible_label = new VisibleLabel();
            visible_label.texts = new List<string>();
            var label_element = label.Label; 
            // essence monolith
            if (label.ItemOnGround.Path == "Metadata/MiscellaneousObjects/Monolith"){
                foreach (var child_element in label_element.Children[1].Children){
                    var text = child_element.Text;
                    if (text != null){
                        visible_label.texts.Add(text);
                    }
                }
            } else if (label.ItemOnGround.Path == "Metadata/MiscellaneousObjects/WorldItem") {
                visible_label.texts.Add(label_element.Text);
                var animated_component = label.ItemOnGround.GetComponent<Animated>();
                if (animated_component != null){
                    visible_label.i_m = animated_component.BaseAnimatedObjectEntity.Path;
                }
            // ultimatum start window
            } else if (label.ItemOnGround.Path == "Metadata/Terrain/Leagues/Ultimatum/Objects/UltimatumChallengeInteractable") {
                try {

                    visible_label.v = label_element.Children[0].IsVisible ? 1 : 0;
                    visible_label.p = label.ItemOnGround.Path;
                    visible_label.id = (int)label.ItemOnGround.Id;
                    // ultimatum type
                    var ultimatum_type = label_element.Children[0].Children[0].Children[1].Children[1].Text;
                    visible_label.texts.Add(ultimatum_type);
                    // ultimatum choices
                    var ultimatum_choices = label_element.Children[0].Children[0].Children[2].Children[0].Children;
                    foreach (var child_element in ultimatum_choices){
                        var text = "???";
                        try {
                            var child_element_nested = child_element.Tooltip.Children[1].Children[3]; 
                            text = child_element_nested.Text;
                        }  catch (Exception ex){
                            DebugWindow.LogMsg($"getvisible lables ultimatum start window choices {ex}");
                        }
                        visible_label.texts.Add(text);
                    }
                    // mod chosen
                    var visible_text = label_element.Children[0].Children[0].Children[4].Children[0].Children[1].Tooltip.IsVisible ? "visible" : "not_visible" ;
                    visible_label.texts.Add(visible_text);
                    var element_rect = label_element.GetClientRect();
                    visible_label.sz = new List<int> { 
                        (int)element_rect.X,
                        (int)(element_rect.X + element_rect.Width),
                        (int)element_rect.Y,
                        (int)(element_rect.Y + element_rect.Height),
                    };
                    visible_labels.Add(visible_label);
                } catch (Exception ex){
                    DebugWindow.LogMsg($"getvisible lables ultimatum start window {ex}");
                }
                continue;
            } else if (label.ItemOnGround.Path == "Metadata/MiscellaneousObjects/Harvest/Irrigator") {
                foreach (var child_element in label_element.Children[1].Children[0].Children[3].Children){
                    var child_element_nested = child_element.Children[0].Children[0]; 
                    var text = child_element_nested.Text;
                    if (text != null){
                        visible_label.texts.Add(text);
                    }
                    visible_label.v = label_element.Children[0].IsVisible ? 1 : 0;
                }
            } else if (label.ItemOnGround.Path == "Metadata/MiscellaneousObjects/Harvest/Extractor") {
                foreach (var child_element in label_element.Children[1].Children[0].Children[3].Children){
                    var child_element_nested = child_element.Children[0].Children[0]; 
                    var text = child_element_nested.Text;
                    if (text != null){
                        visible_label.texts.Add(text);
                    }
                }
            } else if (label.ItemOnGround.Path == "Metadata/MiscellaneousObjects/PrimordialBosses/CleansingFireAltar") {
                foreach (var altar_element in label_element.Children){
                    VisibleLabel atlar_label = new VisibleLabel();
                    atlar_label.texts = new List<string>();

                    atlar_label.texts.Add(altar_element.Children[1].Text);

                    atlar_label.p = label.ItemOnGround.Path;
                    atlar_label.id = (int)label.ItemOnGround.Id;
            
                    atlar_label.p_o_s = new Posx1x2y1y2();
                    atlar_label.p_o_s.x1 = (int)altar_element.GetClientRect().X;
                    atlar_label.p_o_s.x2 = (int)(altar_element.GetClientRect().X + altar_element.GetClientRect().Width);
                    atlar_label.p_o_s.y1 = (int)altar_element.GetClientRect().Y;
                    atlar_label.p_o_s.y2 = (int)(altar_element.GetClientRect().Y + altar_element.GetClientRect().Height);
                    visible_labels.Add(atlar_label);
                }
                continue;
             }else if (label.ItemOnGround.Path == "Metadata/Terrain/Leagues/Necropolis/Objects/NecropolisCorpseMarker") {
                VisibleLabel necropolis_label = new VisibleLabel();
                necropolis_label.texts = new List<string>();

                necropolis_label.p = label.ItemOnGround.Path;
                necropolis_label.id = (int)label.ItemOnGround.Id;
                
                var necropolis_label_element = label.Label.Children[0].Children[2].Children[1].GetClientRect();
                // var necropolis_label_element = label.Label.Children[0].Children[2].Children[0].Children[0].GetClientRect();
                necropolis_label.p_o_s = new Posx1x2y1y2();
                necropolis_label.p_o_s.x1 = (int)necropolis_label_element.X;
                necropolis_label.p_o_s.x2 = (int)(necropolis_label_element.X + necropolis_label_element.Width);
                necropolis_label.p_o_s.y1 = (int)necropolis_label_element.Y;
                necropolis_label.p_o_s.y2 = (int)(necropolis_label_element.Y + necropolis_label_element.Height);
                
                visible_labels.Add(necropolis_label);
                continue;
            } else {
                continue;
            }

            visible_label.p = label.ItemOnGround.Path;
            visible_label.id = (int)label.ItemOnGround.Id;
            visible_label.p_o_s = new Posx1x2y1y2();
            visible_label.p_o_s.x1 = (int)label_element.GetClientRect().X;
            visible_label.p_o_s.x2 = (int)(label_element.GetClientRect().X + label_element.GetClientRect().Width);
            visible_label.p_o_s.y1 = (int)label_element.GetClientRect().Y;
            visible_label.p_o_s.y2 = (int)(label_element.GetClientRect().Y + label_element.GetClientRect().Height);
            
            visible_labels.Add(visible_label);
        }
        return visible_labels;
    }
    public List<VisibleLabelEntity_c> getVisibleLabelOnGroundEntities(){
        List<VisibleLabelEntity_c> visible_labels = new List<VisibleLabelEntity_c>();
        foreach (var label in GameController.IngameState.IngameUi.ItemsOnGroundLabelElement.LabelsOnGroundVisible){
            var obj = label.ItemOnGround;
            // ignore invalid or temp objects
            if (obj.IsValid != true){
                continue;
            }
            
            // ignore effect objects
            if (obj.Type == EntityType.Effect){
                continue;
            }
            VisibleLabelEntity_c entity = new VisibleLabelEntity_c();
            entity.i = (int)obj.Id;
            entity.p = obj.Path;
            entity.gp = new List<int> { (int)obj.GridPos.X, (int)obj.GridPos.Y };
            entity.wp = new List<int> { (int)obj.BoundsCenterPos.X,(int)obj.BoundsCenterPos.Y,(int)obj.BoundsCenterPos.Z };
            // entity_type
            entity.et = serializeEntityType(obj.Type.ToString());
            // BoundsCenterPos
            // need for checking if item is collectable
            try {
                if ((int)obj.BoundsCenterPos.X != 0){
                    entity.b = 1;
                } else {
                    entity.b = 0;
                }
            }
            catch (Exception e){
                DebugWindow.LogMsg($"getVisibleLabelOnGroundEntities BoundsCenterPos -> {e}");
            } 

            // loc on screen
            try {
                int loc_on_screen_x = 0;
                int loc_on_screen_y = 0;

                if ((int)obj.BoundsCenterPos.X != 0){
                    var loc_on_screen = GameController.IngameState.Camera.WorldToScreen(obj.BoundsCenterPos);
                    loc_on_screen_x = (int)loc_on_screen.X;
                    loc_on_screen_y = (int)loc_on_screen.Y;
                } else if (entity.et == "wi") {
                    continue;
                }

                entity.ls = new List<int> { loc_on_screen_x, loc_on_screen_y };
            }
            catch (Exception e){
                DebugWindow.LogMsg($"getVisibleLabelOnGroundEntities -> {e}");
            }

            // render name # need only for area transitions
            entity.rn = obj.RenderName;

            // is_targetable
            try {
                entity.t = obj.IsTargetable ? 1 : 0;
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"Targetable -> {e}");
            }
            visible_labels.Add(entity);
        };
        return visible_labels;
    }
    public PlayerInfo_c getPlayerInfo(){
        var playerLife  = GameController.Game.IngameState.Data.LocalPlayer.GetComponent<Life>();
        PlayerInfo_c player_info = new PlayerInfo_c();
        player_info.b = new List<string>();
        player_info.gp = new List<int>{
            (int)GameController.EntityListWrapper.Player.GridPos.X,
            (int)GameController.EntityListWrapper.Player.GridPos.Y
        };
        player_info.l = new List<int> { 
                playerLife.MaxHP,
                playerLife.CurHP,
                playerLife.Health.Reserved,
                playerLife.MaxMana,
                playerLife.CurMana,
                playerLife.Mana.Reserved,
                playerLife.MaxES,
                playerLife.CurES,
                playerLife.EnergyShield.Reserved,
            };
        foreach (var buff in GameController.Player.Buffs){
            player_info.b.Add(buff.Name);
        }
        var player_comp  = GameController.Game.IngameState.Data.LocalPlayer.GetComponent<Player>();
        if (player_comp != null){
            player_info.lv = player_comp.Level;
        };
        return player_info;
    }
    public SkillsOnBar_c getSkillBar(bool detailed = false){
        SkillsOnBar_c skill_bars = new SkillsOnBar_c();
        skill_bars.c_b_u = new List<int>();
        skill_bars.cs = new List<int>();
        skill_bars.i_n = new List<string>();
        skill_bars.d = new List<List<Dictionary<string, int>>>();
        foreach (var skill_bar_element in GameController.IngameState.IngameUi.SkillBar.Skills){
            ActorSkill skill_element = skill_bar_element.Skill;
            int can_be_used = 0;
            if (skill_element.CanBeUsed == true){
                can_be_used = 1;
            }
            skill_bars.c_b_u.Add(can_be_used);
            skill_bars.cs.Add(skill_element.HundredTimesAttacksPerSecond);

            if (detailed == true){
                skill_bars.i_n.Add(skill_element.InternalName);
                var stats_list = new List<Dictionary<string, int>>(); 
                foreach (var skill_stat in skill_element.Stats){
                    stats_list.Add(new Dictionary<string, int>{{skill_stat.Key.ToString(), skill_stat.Value}});
                }
                skill_bars.d.Add(stats_list);
            }
        }
        return skill_bars;
    }
    public FlasksOnBar getFlasksInfo(bool detailed = true){
        FlasksOnBar flasks_info = new FlasksOnBar();
        flasks_info.cu = new List<int>();
        flasks_info.i = new List<int>();
        flasks_info.n = new List<string>();

        foreach (var inventory in GameController.IngameState.Data.ServerData.PlayerInventories){
            if (inventory.Inventory.InventType == InventoryTypeE.Flask){
                var flask_items = inventory.Inventory.InventorySlotItems;
                foreach (var flask_item in flask_items){
                    var item = flask_item.Item;
                    var charges_component = item.GetComponent<Charges>();
                    int can_use = 0;
                    if (charges_component.NumCharges >= charges_component.ChargesPerUse){
                        can_use = 1;
                    }
                    flasks_info.cu.Add(can_use);
                    flasks_info.i.Add((int)flask_item.InventoryPosition.X);
                    flasks_info.n.Add(item.GetComponent<Base>().Name);
                }
                break;
            } else {
                continue;
            }
        }
        return flasks_info;
    }
    public InventoryObjectCustom_c convertItem(Entity orig_item){
        InventoryObjectCustom_c converted_item = new InventoryObjectCustom_c();
        converted_item.RenderArt = orig_item.Metadata;
        converted_item.Name = orig_item.GetComponent<Base>().Name;
        converted_item.item_mods = new List<string>();
        converted_item.imr = new List<string>();
        
        converted_item.c = 0;
        if (orig_item.GetComponent<Base>().isCorrupted == true){
            converted_item.c = 1;
        }

        Stack stack_component = orig_item.GetComponent<Stack>();
        converted_item.items_in_stack = 0;
        if (stack_component != null){
            converted_item.items_in_stack = stack_component.Size;
        }
        
        var map_component = orig_item.GetComponent<ExileCore2.PoEMemory.Components.Map>();
        converted_item.m_t = 0;
        if (map_component != null){
            converted_item.m_t = map_component.Tier;
        }

        // icon?
        var render_item_component = orig_item.GetComponent<RenderItem>();
        if (render_item_component != null){
            converted_item.a = render_item_component.ResourcePath;
        }

        var sockets_component = orig_item.GetComponent<Sockets>();
        if (sockets_component != null){
            converted_item.l = sockets_component.SocketGroup;
        }

        Mods mods_component = orig_item.GetComponent<Mods>();
        if (mods_component != null){
            converted_item.unique_name = mods_component.UniqueName;
            converted_item.rarity = mods_component.ItemRarity.ToString();
            foreach (var mod in mods_component.HumanImpStats){
                converted_item.item_mods.Add(mod);
            } 
            foreach (var mod in mods_component.HumanStats){
                converted_item.item_mods.Add(mod);
            }
            foreach (var mod in mods_component.ItemMods){
                converted_item.imr.Add(mod.RawName);
            }
            converted_item.i = 0;
            if (mods_component.Identified == true){
                converted_item.i = 1;
            }
        }

        return converted_item;
    }
    
    public GetMapDeviceInfoObject mapDeviceInfo(){
        GetMapDeviceInfoObject map_device_info = new GetMapDeviceInfoObject();
        var atlas_panel_object = GameController.IngameState.IngameUi.WorldMap.AtlasPanel;
        map_device_info.ap_o = GameController.IngameState.IngameUi.WorldMap.IsVisible;
        map_device_info.wm_o = atlas_panel_object.IsVisible;
        if (atlas_panel_object.IsVisible == false){
            return map_device_info;
        }



        List<WorldMapEndGameMapObj> avaliable_maps  = new List<WorldMapEndGameMapObj>();
        var maps = atlas_panel_object.Descriptions;
        foreach (var tile in maps){
            var mapElement = tile.Element;
            if (mapElement.IsUnlocked == false || mapElement.IsVisited == true){
                continue;
            }
            WorldMapEndGameMapObj map_obj = new WorldMapEndGameMapObj();
            map_obj.name = mapElement.Area.Name;
            map_obj.name_raw = mapElement.Area.Id;
            map_obj.id = mapElement.IndexInParent ?? 0;

            var el_rect = mapElement.GetClientRect();
            map_obj.sz = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };

            map_obj.icons = new List<string>();
            foreach (var m in mapElement.Children[0].Children){
                map_obj.icons.Add(m.TextureName);
            }
            avaliable_maps.Add(map_obj);
        }
        map_device_info.av_m = avaliable_maps;

        // place map window
        var world_map_object = GameController.IngameState.IngameUi.WorldMap;
        int world_map_children_count = world_map_object.Children.Count;

        // int running_iter = world_map_children_count - 2;
        // while (running_iter < world_map_children_count){
        for (int running_iter = world_map_children_count - 2; running_iter < world_map_children_count; running_iter++){
            var child_element = world_map_object.Children[running_iter];
            if (child_element.Children.Count == 3){
                var place_map_window_element = child_element;
                map_device_info.pmw_o = place_map_window_element.IsVisible;
                if (place_map_window_element.IsVisible == false){
                    break;
                }

                var placemapwindowelementrectangle = place_map_window_element.GetClientRect();
                map_device_info.pmw_sz = new List<int> {
                    (int)placemapwindowelementrectangle.X, 
                    (int)(placemapwindowelementrectangle.X + placemapwindowelementrectangle.Width), 
                    (int)placemapwindowelementrectangle.Y, 
                    (int)(placemapwindowelementrectangle.Y + placemapwindowelementrectangle.Height), 
                };

                var activatebuttonreactangle = place_map_window_element.Children[1].Children[5].Children[1].GetClientRect();
                map_device_info.pmw_ab_sz = new List<int> {
                    (int)activatebuttonreactangle.X, 
                    (int)(activatebuttonreactangle.X + activatebuttonreactangle.Width), 
                    (int)activatebuttonreactangle.Y, 
                    (int)(activatebuttonreactangle.Y + activatebuttonreactangle.Height), 
                };




                var items_placed_in_map_device_parent = place_map_window_element.Children[1].Children[5].Children[0];
                List<InventoryObjectCustom_c> items  = new List<InventoryObjectCustom_c>();
                int i_start = 1;
                int i_end = items_placed_in_map_device_parent.Children.Count;
                // get info about items in slots
                for (int i = i_start; i < i_end; i++){
                    InventoryObjectCustom_c item = new InventoryObjectCustom_c();
                    try {
                        var item_info = items_placed_in_map_device_parent.Children[i];
                        item = convertItem(item_info.Entity);
                        var item_rect = item_info.GetClientRect();
                        item.s = new List<int> {
                            (int)item_rect.X, 
                            (int)(item_rect.X + item_rect.Width), 
                            (int)item_rect.Y, 
                            (int)(item_rect.Y + item_rect.Height), 
                        };
                    } catch (Exception ex){
                        // DebugWindow.LogMsg($"sharedata mapDeviceInfo for items -> {ex}");
                    }
                    items.Add(item);
                }
                map_device_info.pmw_i = items;

                break;
            }
            // running_iter += 1;
        }

        return map_device_info;

    }
    
    public List<string> getPreloadedFiles(){
        List<string> preloaded_files_arr = new List<string>();
        var memory = GameController.Memory;
        FilesFromMemory filesFromMemory = new FilesFromMemory(memory);
        var AllFiles = filesFromMemory.GetAllFilesSync();
        int areaChangeCount = GameController.Game.AreaChangeCount;
        foreach (var file in AllFiles)
        {
            if (file.Value.ChangeCount == areaChangeCount)
            {
                var text = file.Key;
                if (text.Contains('@')) text = text.Split('@')[0];
                preloaded_files_arr.Add(text);
            }
        }
        return preloaded_files_arr;
    }
    public List<GemToLevelInfo> getGemsToLevelInfo(){
        List<GemToLevelInfo> gems_to_level = new List<GemToLevelInfo>();
        foreach (var gem in GameController.IngameState.IngameUi.GemLvlUpPanel.GemsToLvlUp){
            GemToLevelInfo gem_instance = new GemToLevelInfo();
            gem_instance.center_location = new LocationOnScreen_generated();
            gem_instance.center_location.X = (int)gem.Center.X;
            gem_instance.center_location.Y = (int)gem.Center.Y;
            gem_instance.height = (int)gem.Height;
            gem_instance.width = (int)gem.Width;
            gems_to_level.Add(gem_instance);
        } 
        return gems_to_level;
    }

    public GetDataObject getData(string type){
        GetDataObject response = new GetDataObject();
        DebugWindow.LogMsg("call getData");
        

        bool detailed = false;
        if (type == "full"){
            detailed = true;
        }

        try{
            // game state
            response.g_s = 0; 
            if (GameController.Game.IsInGameState == true){
                response.g_s = 20;
            } else if (GameController.Game.IsLoginState == true){
                response.g_s = 1;
            } else if (GameController.Game.IsSelectCharacterState){
                response.g_s = 10;
            }

            // window related
            // window pos
            var window = GameController.Window.GetWindowRectangleTimeCache;
            response.w = new List<int> {
                (int)window.BottomLeft.X, 
                (int)window.TopRight.X, 
                (int)window.TopRight.Y, 
                (int)window.BottomLeft.Y, 
            };

            // area related
            response.IsLoading = GameController.Game.IsLoading;
            response.ipv = GameController.IngameState.IngameUi.InvitesPanel.IsVisible;
            response.IsLoading_b = false;

            foreach (var game_state in GameController.Game.ActiveGameStates){
                int match_count = 0; 
                var game_state_str = $"{game_state.Address:X}";
                // DebugWindow.LogMsg($"checking full {game_state_str}");
                var game_state_str_last_three = game_state_str.Substring(10-2);
                // DebugWindow.LogMsg($"checking three {game_state_str_last_three}");
                foreach (var current_game_state in GameController.Game.CurrentGameStates){
                    var curr_game_state_str = $"{current_game_state.Address:X}";
                    var curr_game_state_str_last_three = curr_game_state_str.Substring(10-2);
                    // DebugWindow.LogMsg($"checking {game_state_str_last_three} in {curr_game_state_str_last_three}");
                    if (game_state_str_last_three == curr_game_state_str_last_three){
                        match_count += 1;
                        // DebugWindow.LogMsg($"match_count {match_count}");
                    }
                }
                // DebugWindow.LogMsg($"match_count {match_count} in {game_state_str_last_three}");
                if (match_count == 2){
                    response.IsLoading_b = true;
                }

            }
            response.area_raw_name = GameController.Area.CurrentArea.Area.RawName;
            response.ah = GameController.Area.CurrentArea.Hash;

            response.pi = getPlayerInfo();
            response.awake_entities = getAwakeEntities();
            response.i = getItemsOnGroundLabelsVisible();
            response.vl = getVisibleLabelOnGroundEntities();
            response.s = getSkillBar(detailed);
            response.f = getFlasksInfo();
        } catch (Exception e) {
            DebugWindow.LogError($"ShareData cannot build player data -> {e}");
        }

        if (detailed == true) {
            response.terrain_string = generateMinimap().ToString();
        }


        DebugWindow.LogMsg("return getData");
        
        return response;

    }
    private async Task ServerRestartEvent()
    {
        DebugWindow.LogError("private IEnumerator ServerRestartEvent()");
        while (true) 
        {
            if (GameController != null)
            {
                if (!ServerIsRunning)
                {
                    ServerIsRunning = true;
                    DebugWindow.LogError("trying to run server");
                    try{
 
                        string endpoint = "http://*:50006/";
                        var ws = new WebServer(SendResponse, endpoint);
                        ws.Run();
                        DebugWindow.LogError("A simple webserver. Press a key to quit.");
                    }
                    catch (Exception e) {
                        DebugWindow.LogError($" ServerRestartEvent was crushed -> {e}");
                    }

                }
            }
            await Task.Delay(500); // Wait for 500 milliseconds asynchronously
            // yield return new WaitTime(500);
        }
    }


    public class Client
    {

        private void SendHeaders(TcpClient Client, int StatusCode, string StatusCodeSuffix)
        {
            string Headers = (
                $"HTTP/1.1 {StatusCode} {StatusCodeSuffix}\n" +
                "Content-Type: application/json\n" +
                "Connection: Keep-Alive\n" +
                "Keep-Alive: timeout=15\n\n"
            );
            byte[] HeadersBuffer = Encoding.UTF8.GetBytes(Headers);
            Client.GetStream().Write(HeadersBuffer, 0, HeadersBuffer.Length);
        }

        private void SendRequest(TcpClient Client, string Content, int StatusCode, string StatusCodeSuffix = "")
        {

            SendHeaders(Client, StatusCode, StatusCodeSuffix);

            byte[] Buffer = Encoding.UTF8.GetBytes(Content);
            Client.GetStream().Write(Buffer, 0, Buffer.Length);
            Client.Close();
        }

        private string ParseRequest1(TcpClient Client)
        {
            string Request = "";
            byte[] Buffer = new byte[1024];
            int Count;

            while ((Count = Client.GetStream().Read(Buffer, 0, Buffer.Length)) > 0)
            {
                Request += Encoding.UTF8.GetString(Buffer, 0, Count);

                if (Request.IndexOf("\r\n\r\n") >= 0 || Request.Length > 4096)
                {
                    break;
                }
            }

            Match ReqMatch = Regex.Match(Request, @"^\w+\s+([^\s\?]+)[^\s]*\s+HTTP/.*|");

            if (ReqMatch == Match.Empty)
            {
                return "";
            }

            return ReqMatch.Groups[1].Value;
        }
        private string ParseRequest(TcpClient Client)
        {
            string Request = "";
            byte[] Buffer = new byte[1024];
            int Count;

            while ((Count = Client.GetStream().Read(Buffer, 0, Buffer.Length)) > 0)
            {
                Request += Encoding.UTF8.GetString(Buffer, 0, Count);

                if (Request.IndexOf("\r\n\r\n") >= 0 || Request.Length > 4096)
                {
                    break;
                }
            }
            // DebugWindow.LogError(Request);

            try
            {
                var some_str = Request.Split(new [] { "GET " }, StringSplitOptions.None)[1].Split(new [] { " HTTP" }, StringSplitOptions.None)[0];
                return some_str;
                
            }
            catch (System.Exception)
            {
                return "";
            }

            Match ReqMatch = Regex.Match(Request, @"^\w+\s+([^\s\?]+)[^\s]*\s+HTTP/.*|");

            if (ReqMatch == Match.Empty)
            {
                return "";
            }

            return ReqMatch.Groups[1].Value;
        }

        public static byte WalkableValue(byte[] data, int bytesPerRow, long c, long r)
        {
            var offset = r * bytesPerRow + c / 2;
            if (offset < 0 || offset >= data.Length)
            {
                throw new Exception(string.Format($"WalkableValue failed: ({c}, {r}) [{bytesPerRow}] => {offset}"));
            }

            byte b;
            if ((c & 1) == 0)
            {
                b = (byte)(data[offset] & 0xF);
            }
            else
            {
                b = (byte)(data[offset] >> 4);
            }
            return b;
        }

        // private TerrainData _terrainMetadata;
        public static StringBuilder generateMinimap()
        {
            StringBuilder sb = new StringBuilder();
            int MapCellSizeI = 23;
            // var _terrainMetadata = GameController.IngameState.Data.DataStruct.Terrain;
            // var MeleeLayerPathfindingData = GameController.Memory.ReadStdVector<byte>(Cast(_terrainMetadata.LayerMelee));

            // var BytesPerRow = _terrainMetadata.BytesPerRow;
            // var Rows = _terrainMetadata.NumRows;
            // var Cols = _terrainMetadata.NumCols;

            // for (var r = Rows * MapCellSizeI - 1; r >= 0; --r)
            // {
            //     for (var c = 0; c < Cols * MapCellSizeI; c++)
            //     {
            //         var b = WalkableValue(MeleeLayerPathfindingData, BytesPerRow, c, r);
            //         // var b = 1;
            //         var ch = b.ToString()[0];
            //         if (b == 0)
            //             ch = '0';
            //         sb.AppendFormat("{0}", ch);
            //     }
            //     sb.AppendLine();
            // }
            return sb;
        }


        public Client(TcpClient Client)
        
        {




            
            try
            {
                string RequestUri = ParseRequest(Client);
                RequestUri = Uri.UnescapeDataString(RequestUri);
                DebugWindow.LogError("got request");
                string unixTimestamp = Convert.ToString((int)DateTime.Now.Subtract(new DateTime(1970, 1, 1)).TotalSeconds);
                DebugWindow.LogError(RequestUri);
                if (RequestUri.Contains("/getData") == true){

                    GetDataObject response = new GetDataObject();

                    var request_type = "partial";
                    try{
                        request_type = RequestUri.Split(new [] { "type=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0];
                        request_type = "full";
                    }
                    catch (Exception ex)
                    {
                        // do none
                    }
                    DebugWindow.LogError("request type is: ");
                    DebugWindow.LogError(request_type);

                    if (request_type == "full"){
                        response.terrain_string = generateMinimap().ToString();
                    } else {
                        response.terrain_string = "";
                    }

                    var content = Newtonsoft.Json.JsonConvert.SerializeObject(response, Newtonsoft.Json.Formatting.Indented);
                    SendRequest(
                        Client,
                        content, 200, "OK"
                    );
                } else if (RequestUri.Contains("/getScreenPos") == true){
                    int y = int.Parse(RequestUri.Split(new [] { "y=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
                    int x = int.Parse(RequestUri.Split(new [] { "x=" }, StringSplitOptions.None)[1].Split(new [] { "&" }, StringSplitOptions.None)[0]);
                    List<float> pos = DataBuilder.getScreenPos(x, y);
                    string content = Newtonsoft.Json.JsonConvert.SerializeObject(pos, Newtonsoft.Json.Formatting.Indented);
                    SendRequest(
                        Client,
                        content, 200, "OK"
                    );
                } 

                Client.Close();

            }
            catch (Exception e) {
                DebugWindow.LogError($"{nameof(Client)} in Client -> {e}");
                Client.Close();
            }
        }
    }

    public class Server
    {
        TcpListener Listener;
        int Port;

        public Server(int ServerPort)
        {
            Port = ServerPort;
        }

        public void RunServer(Object StateInfo)
        {
            try
            {
                Listener = new TcpListener(IPAddress.Any, Port);
                Listener.Start();
                
                ServerIsRunning = true;
                
                while (ServerIsRunning)
                {
                    ThreadPool.QueueUserWorkItem(new WaitCallback(ClientThread), Listener.AcceptTcpClient());
                }

                Listener.Stop();
            }
            catch (Exception e) {
                DebugWindow.LogError($"{nameof(Server)} was crashed -> {e}");
                using (StreamWriter sw = new StreamWriter("ShareDataCrashLog")) 
                {
                    sw.Write($"{nameof(Server)} was crushed -> {e}");
                }
                ServerIsRunning = false;
                Listener.Stop();
                return;
            }
        }

        public void ClientThread(Object StateInfo)
        {
            try
            {
                new Client((TcpClient)StateInfo);
            }
            catch (Exception e) {
                DebugWindow.LogError($"{nameof(Server)} ClientThread was crushed -> {e}");
            }
        }
    }
}
