using System;
using System.Net;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Net.Sockets;
using System.IO;
using System.Net.Http;

using ExileCore2;
using ExileCore2.PoEMemory;
using ExileCore2.PoEMemory.Components;
using ExileCore2.PoEMemory.MemoryObjects;
using ExileCore2.Shared.Enums;
using GameOffsets2.Native;
using Stack = ExileCore2.PoEMemory.Components.Stack;
// 111 9 11 0 deli activator thing

namespace ShareData;
public class ShareData : BaseSettingsPlugin<ShareDataSettings>
{
    private static int update_frequency_per_sec = 20;
    private static List<string> data_cache = new List<string>(["", ""]);
    private static readonly object dataTempLock = new object();  // Lock object for thread-safety

    public override bool Initialise()
    {
        GameController.LeftPanel.WantUse(() => Settings.Enable);
        Task.Run(() => ServerRestartEvent());
        Task.Run(() => StartHttpServer()); // Start the HTTP server
        Task.Run(() => startUpdatingCache()); // cache
        return true;
    }
    private async Task StartHttpServer()
    {
        int httpPort = 50005;
        HttpListener listener = new HttpListener();
        listener.Prefixes.Add($"http://*:{httpPort}/");
        listener.Start();
        DebugWindow.LogMsg($"HTTP server started on port {httpPort}...");

        while (true)
        {
            await Task.Delay(50);
            HttpListenerContext context = await listener.GetContextAsync();
            _ = HandleHttpRequestAsync(context); // Handle each HTTP request asynchronously
        }
    }

    private async Task startUpdatingCache()
    {
        await Task.Delay(100);
        int started_at_ms = Environment.TickCount;
        while (true)
        {
            // Get new data and serialize it
            string data;
            try
            {
                DebugWindow.LogMsg($"update cache");
                data = SerializeData(getData("partial"));
            }
            catch (Exception ex)
            {
                DebugWindow.LogError($"update cache error: {ex}");
                await Task.Delay(10);
                continue;
            }

            // Thread-safe access to data_temp (using lock)
            lock (dataTempLock)
            {
                // Remove the oldest entry if the list has more than a certain number of entries
                if (data_cache.Count > 10) // Adjust threshold as needed
                {
                    data_cache.RemoveAt(0);
                }
                data_cache.Add(data);
            }

            int ended_at_ms = Environment.TickCount;
            int elapsed_time_ms = ended_at_ms - started_at_ms;

            // Calculate the delay needed to maintain the update frequency
            int wait_for_ms = (1000 / update_frequency_per_sec) - elapsed_time_ms;

            if (wait_for_ms > 0)
            {
                await Task.Delay(wait_for_ms);
            }
            started_at_ms = Environment.TickCount;
        }
    }

    private async Task HandleHttpRequestAsync(HttpListenerContext context)
    {
        try
        {
            string rawRequest = context.Request.Url.LocalPath;
            string query = context.Request.Url.Query;

            string response = ProcessRequest(rawRequest + query);

            byte[] buffer = Encoding.UTF8.GetBytes(response);
            context.Response.ContentLength64 = buffer.Length;
            await context.Response.OutputStream.WriteAsync(buffer, 0, buffer.Length);
            context.Response.OutputStream.Close();
        }
        catch (Exception ex)
        {
            DebugWindow.LogError($"HTTP request error: {ex}");
        }
    }
    private async Task ServerRestartEvent()
    {
        int serverPort = 50006;
        var listener = new TcpListener(IPAddress.Any, serverPort);
        listener.Start();
        DebugWindow.LogMsg($"TCP server started on port {serverPort}...");

        while (true)
        {
            await Task.Delay(10);
            var client = await listener.AcceptTcpClientAsync();
            _ = HandleClientAsync(client); // Handle each client asynchronously
        }
    }
    private async Task HandleClientAsync(TcpClient client)
    {
        try
        {
            using (client)
            using (var stream = client.GetStream())
            using (var reader = new StreamReader(stream, Encoding.UTF8))
            using (var writer = new StreamWriter(stream, Encoding.UTF8) { AutoFlush = true })
            {
                while (true)
                {
                    string request = await reader.ReadLineAsync();
                    if (request == null) break; // Client disconnected

                    string response = ProcessRequest(request);
                    await writer.WriteLineAsync(response);
                }
            }
        }
        catch (Exception ex)
        {
            DebugWindow.LogError($"Client error: {ex}");
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

        // for (var r = 0; r < Rows * MapCellSizeI; r++)
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
            entity.id = (int)obj.Id;
            if (entity.id < 0){
                continue;
            }
            entity.path = obj.Path;
            entity.grid_position = new List<int> { (int)obj.GridPos.X, (int)obj.GridPos.Y };
            entity.world_position = new List<int> { (int)obj.BoundsCenterPos.X,(int)obj.BoundsCenterPos.Y,(int)obj.BoundsCenterPos.Z };
            // life component if it has it
            try
            {
                var obj_life = obj.GetComponent<Life>();
                entity.life_component = new List<int> { 
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
            entity.entity_type = serializeEntityType(obj.Type.ToString());

            // BoundsCenterPos
            // need for checking if item is collectable
            try {
                if ((int)obj.BoundsCenterPos.X != 0){
                    entity.bound_center_pos = 1;
                } else {
                    entity.bound_center_pos = 0;
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
                } else if (entity.entity_type == "wi") {
                    continue;
                }

                entity.location_on_screen = new List<int> { loc_on_screen_x, loc_on_screen_y };
            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities -> {e}");
                
            }



            // render name # need only for area transitions
            entity.render_name = obj.RenderName;

            // Rarity
            try {
                entity.rarity = obj.Rarity.ToString();

            }
            catch (Exception e)
            {
                DebugWindow.LogMsg($"getAwakeEntities -> {e}");
                
            } 

            // IsHostile
            try {
                entity.is_hostile = obj.IsHostile ? 1 : 0;

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
                entity.is_attackable = 0;
            } else {
                entity.is_attackable = 1;
            }

            // essenced_mob
            entity.essenced_mob = 0;
            if (entity.is_attackable == 1) {
                var magic_properties = obj.GetComponent<ObjectMagicProperties>();
                if (magic_properties != null){
                    if (magic_properties.Rarity == MonsterRarity.Rare){
                        var buffs_component = obj.GetComponent<Buffs>();
                        if (buffs_component != null){
                            if (buffs_component.HasBuff("hidden_monster_disable_minions")){
                                entity.essenced_mob = 1;
                            };
                        }
                        // foreach (var mod_str in magic_properties.Mods){
                        //     if (mod_str.Contains("EssenceDaemon") == true){
                        //         entity.em = 1;
                        //         break;
                        //     }
                        // }
                    }
                }
            }


            // is_opened
            entity.is_opened = 0;
            
            if (entity.path == "Metadata/Terrain/Leagues/Ritual/RitualRuneInteractable"){
                var state_machine_component = obj.GetComponent<StateMachine>();
                if (state_machine_component != null){
                    entity.is_opened = state_machine_component.States.Any(state => state.Name == "current_state" && state.Value == 2) ? 1 : 0;
                }
            } else if (entity.path == "Metadata/Terrain/Gallows/Leagues/Delirium/Objects/DeliriumInitiator"){
                var state_machine_component = obj.GetComponent<StateMachine>();
                if (state_machine_component != null){
                    entity.is_opened = state_machine_component.States.Any(state => state.Name == "interacted" && state.Value == 1) ? 1 : 0;
                }
            } else {
                var triggerable_blockage = obj.GetComponent<TriggerableBlockage>();
                if (triggerable_blockage != null){
                    entity.is_opened = triggerable_blockage.IsOpened ? 1 : 0;
                }
            }
            
            // "Metadata/Monsters/LeagueDelirium/DoodadDaemons/DoodadDaemonShardPack<whatevergoesnext>
            // state machine
            // "detonated": 1 == isOpened

            // "Metadata/MiscellaneousObjects/Breach/BreachObject" it has "is_transitioned" property


            // is_targetable
            entity.is_targetable = 0;
            entity.is_targeted = 0;
            var targetable_comp = obj.GetComponent<Targetable>();
            if (targetable_comp != null){
                entity.is_targetable = targetable_comp.isTargetable ? 1 : 0;
                entity.is_targeted = targetable_comp.isTargeted ? 1 : 0;
            }
            // try {
            //     entity.t = obj.IsTargetable ? 1 : 0;
            // }
            // catch (Exception e)
            // {
            //     DebugWindow.LogMsg($"Targetable -> {e}");
            // }


            // // AnimatedPropertiesMetadata
            // var animated_metadata = obj.GetComponent<Animated>();
            // if (animated_metadata != null){
            //     entity.a = animated_metadata.BaseAnimatedObjectEntity.Metadata;
            // }

            awake_entities.Add(entity);
        }
        return awake_entities;
    }
    public List<string> TraverseElementsBFS(Element root)
    {
        var result = new List<string>();
        if (root == null) return result;

        var queue = new Queue<Element>();
        queue.Enqueue(root);

        while (queue.Count > 0)
        {
            var currentElement = queue.Dequeue();

            // Add the current element's text to the result list
            if (currentElement.TextNoTags != null)
            {
                result.Add(currentElement.TextNoTags);
            }

            // Add the current element's tooltip text (if available)
            if (currentElement.Tooltip != null && currentElement.Tooltip.TextNoTags != null)
            {
                result.Add($"Tooltip: {currentElement.Tooltip.TextNoTags}");
            }

            // Enqueue children for further traversal
            foreach (var child in currentElement.Children)
            {
                queue.Enqueue(child);
            }
        }

        return result;
    }
    public InventoryObjectCustom_c getHoveredItemInfo()
    {
        InventoryObjectCustom_c hovered_item = new InventoryObjectCustom_c();
        var hovered_item_el = GameController.IngameState.UIHoverElement;
        var tooltip_texts_el = hovered_item_el.Tooltip;

        if (tooltip_texts_el != null)
        {
            // Traverse the entire tooltip UI tree
            var items = TraverseElementsBFS(tooltip_texts_el);
            hovered_item.tooltip_texts = items.Where(item => item != null).ToList();
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

            response.tab_buttons_screen_zones = new List<List<int>>();
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
                response.tab_buttons_screen_zones.Add(x1x2y1y2);

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
        inventory_info.is_opened = inventory_panel_element.IsVisible;
        if ( inventory_panel_element.Address == 0){
            inventory_info.is_opened = false;
        }
        
        List<InventoryObjectCustom_c> items = new List<InventoryObjectCustom_c>();
        foreach (var normal_inventory_item in GameController.IngameState.Data.ServerData.PlayerInventories[0].Inventory.InventorySlotItems){
            var item = normal_inventory_item.Item;
            InventoryObjectCustom_c generated_inventory_object = convertItem(item);
            var el_rect = normal_inventory_item.GetClientRect();
            // screen_zone
            generated_inventory_object.screen_zone = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };
            // grid_position
            generated_inventory_object.grid_position = new List<int> {
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

    public PurchaseWindowHideout_c getPurchaseWindowHideoutUi(){
        PurchaseWindowHideout_c el = new();
        var ui_element = GameController.IngameState.IngameUi.PurchaseWindowHideout;
        el.is_visible = ui_element.IsVisible ? 1 : 0;
        if (el.is_visible == 0){
            return el;
        }
        var el_rect = ui_element.GetClientRect(); // label_element_rect
        el.screen_zone = new List<int> {
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
                generated_inventory_object.screen_zone = new List<int> {
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
    public RitualUi_c getRitualUi(){
        RitualUi_c ritual_ui = new RitualUi_c();
        ritual_ui.purchase_menu_is_visible = 0;
        var ritual_button_element = GameController.IngameState.IngameUi.GetChildFromIndices([111, 9, 12, 0]);
        if (ritual_button_element.IsVisible == false){
            ritual_ui.ritual_button_is_visible = 0;
            return ritual_ui;
        }

        // ritual_ui.rt_b_v = ritual_button_element.IsVisible ? 1 : 0;
        ritual_ui.ritual_button_is_visible = 1;

        var ritual_button_rect = ritual_button_element.GetClientRect();
        ritual_ui.ritual_button_screen_zone = new List<int> {
            (int)ritual_button_rect.X, 
            (int)(ritual_button_rect.X + ritual_button_rect.Width), 
            (int)ritual_button_rect.Y, 
            (int)(ritual_button_rect.Y + ritual_button_rect.Height), 
        };

        var tribute_element = GameController.IngameState.IngameUi.GetChildFromIndices([11, 1]);
        if (tribute_element != null && tribute_element.IsVisible == true){
            ritual_ui.tribute = tribute_element.TextNoTags;
        }
        var ritual_progress_element = GameController.IngameState.IngameUi.GetChildFromIndices([111, 9, 12, 0, 0, 0]);
        if (ritual_progress_element != null && ritual_progress_element.IsVisible == true){
            ritual_ui.progress = ritual_progress_element.TextNoTags;
        }

        var ritual_ui_element = GameController.IngameState.IngameUi.RitualWindow;
        if (ritual_ui_element.IsVisible == true){
            ritual_ui.purchase_menu_is_visible = 1;
            var ritual_ui_rect = ritual_ui_element.GetClientRect();
            ritual_ui.purchase_menu_screen_zone = new List<int> {
                (int)ritual_ui_rect.X, 
                (int)(ritual_ui_rect.X + ritual_ui_rect.Width), 
                (int)ritual_ui_rect.Y, 
                (int)(ritual_ui_rect.Y + ritual_ui_rect.Height), 
            };

            
            var defer_button_element = ritual_ui_element.GetChildAtIndex(12);
            ritual_ui.defer_button_text_raw = defer_button_element.GetChildAtIndex(0).TextNoTags;
            var defer_button_rect = defer_button_element.GetClientRect();
            ritual_ui.defer_button_screen_zone = new List<int> {
                (int)defer_button_rect.X, 
                (int)(defer_button_rect.X + defer_button_rect.Width), 
                (int)defer_button_rect.Y, 
                (int)(defer_button_rect.Y + defer_button_rect.Height), 
            };


            var reroll_button_element = ritual_ui_element.GetChildFromIndices([11, 0]);
            var reroll_button_rect = reroll_button_element.GetClientRect();
            ritual_ui.reroll_button_screen_zone = new List<int> {
                (int)reroll_button_rect.X, 
                (int)(reroll_button_rect.X + reroll_button_rect.Width), 
                (int)reroll_button_rect.Y, 
                (int)(reroll_button_rect.Y + reroll_button_rect.Height), 
            };
            ritual_ui.reroll_button_tooltip_text = reroll_button_element.Tooltip.TextNoTags;
            ritual_ui.items = new List<InventoryObjectCustom_c>();
            foreach (var normal_inventory_item in ritual_ui_element.Items){
                var item = convertItem(normal_inventory_item.Entity);
                var item_rect = normal_inventory_item.GetClientRect();
                item.screen_zone = new List<int> {
                    (int)item_rect.X, 
                    (int)(item_rect.X + item_rect.Width), 
                    (int)item_rect.Y, 
                    (int)(item_rect.Y + item_rect.Height), 
                };
                ritual_ui.items.Add(item);
            }
        }


        return ritual_ui;
    }
    public AuctionHouseUi_c getAuctionHouseUi(){
        AuctionHouseUi_c auction_house_ui = new AuctionHouseUi_c();
        var auction_house_element = GameController.IngameState.IngameUi.CurrencyExchangePanel;
        auction_house_ui.is_visible = auction_house_element.IsVisible ? 1 : 0;
        if (auction_house_element.IsVisible == false){
            return auction_house_ui;
        }
        auction_house_ui.screen_zone = getListOfIntFromElRect(auction_house_element);
        auction_house_ui.i_want_button_screen_zone = getListOfIntFromElRect(auction_house_element.GetChildAtIndex(7));
        auction_house_ui.i_want_field_screen_zone = getListOfIntFromElRect(auction_house_element.GetChildAtIndex(5));
        auction_house_ui.i_have_button_screen_zone = getListOfIntFromElRect(auction_house_element.GetChildAtIndex(10));
        auction_house_ui.i_have_field_screen_zone = getListOfIntFromElRect(auction_house_element.GetChildAtIndex(8));
        auction_house_ui.place_order_button_screen_zone = getListOfIntFromElRect(auction_house_element.GetChildAtIndex(15));

        auction_house_ui.gold_in_inventory = GameController.IngameState.IngameUi.InventoryPanel.GetChildFromIndices([3,3,1]).Text;
        auction_house_ui.deal_cost_gold = auction_house_element.GetChildAtIndex(14).TextNoTags;
        var offered_item_element = auction_house_element.GetChildFromIndices([10,0]);
        if (offered_item_element != null){
            auction_house_ui.i_have_item_name = offered_item_element.Text;
        }
        var wanted_item_element = auction_house_element.GetChildFromIndices([7,0]);
        if (wanted_item_element != null){
            auction_house_ui.i_want_item_name = wanted_item_element.Text;
        }
        if (offered_item_element != null && wanted_item_element != null){
            var market_ratio_element = auction_house_element.GetChildAtIndex(13);
            if (market_ratio_element != null){
                auction_house_ui.market_ratios_texts = new List<string>();
                var ratios = market_ratio_element.Tooltip.Children.Skip(2).ToArray();
                foreach (var ratio in ratios)
                {
                    auction_house_ui.market_ratios_texts.Add(ratio.TextNoTags);
                }
            }
        }
        // currency picker
        auction_house_ui.currency_picker = new AuctionHouseUiCurrencyPicker_c();
        auction_house_ui.currency_picker.is_visible = 0;
        var currency_picker_element = auction_house_element.GetChildAtIndex(19);
        if (currency_picker_element != null && currency_picker_element.IsVisible == true){
            auction_house_ui.currency_picker.is_visible = 1;
            auction_house_ui.currency_picker.screen_zone = getListOfIntFromElRect(currency_picker_element);
            // categories
            auction_house_ui.currency_picker.categories = new List<AuctionHouseUiCurrencyPickerCategory_c>();
            var categories_element = currency_picker_element.GetChildFromIndices([5,2]);
            foreach (var item in categories_element.Children){
                var category = new AuctionHouseUiCurrencyPickerCategory_c();
                category.text = item.Children[0].Text;
                category.screen_zone = getListOfIntFromElRect(item);
                auction_house_ui.currency_picker.categories.Add(category);
            }
            // presented elements
            auction_house_ui.currency_picker.presented_elements = new List<AuctionHouseUiCurrencyPickerElements_c>();
            var presented_elements_sections_parent = currency_picker_element.GetChildFromIndices([6,1]);
            foreach (var section in presented_elements_sections_parent.Children){
                if(section.IsVisible == false){
                    continue;
                }
                foreach (var section_subcategory in section.Children){
                    // skip [0] since its header
                    foreach (var subcategory_item in section_subcategory.Children.Skip(1).ToArray()){
                        var picker_element = new AuctionHouseUiCurrencyPickerElements_c();
                        picker_element.screen_zone = getListOfIntFromElRect(subcategory_item);
                        picker_element.text = subcategory_item.Children[0].Text;
                        var item_count = subcategory_item.GetChildFromIndices([1,0]).Text;
                        picker_element.count = item_count == null ? "0" : item_count;
                        auction_house_ui.currency_picker.presented_elements.Add(picker_element);
                    }
                }              
            }
        }
        // current orders
        return auction_house_ui;
    }
    public List<int> getListOfIntFromElRect(Element el){
        var el_rect = el.GetClientRect();
        return  new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
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
            if (minimap_object_component == null){
                continue;
            }
            entity.is_hidden = minimap_object_component.IsHide ? 1 : 0;
            entity.is_visible = minimap_object_component.IsVisible ? 1 : 0;
            entity.name = minimap_object_component.Name;
            entity.id = (int)obj.Id;
            entity.path = obj.Path;
            awake_entities.Add(entity);
        }
        return awake_entities;
    }

    public NpcDialogueUi_c getNpcDialogueUi(){
        NpcDialogueUi_c el = new NpcDialogueUi_c();
        el.is_visible = 1;
        el.choices = new List<NpcDialogueUiChoice_c>();
        var elements_to_iterate = new List<Element>();
        if (GameController.IngameState.IngameUi.ExpeditionNpcDialog.IsVisible == true){
            // var el_rect = GameController.IngameState.IngameUi.ExpeditionNpcDialog.GetClientRect();
            el.screen_zone = getListOfIntFromElRect(GameController.IngameState.IngameUi.ExpeditionNpcDialog);
            var dialog_el = GameController.IngameState.IngameUi.ExpeditionNpcDialog.Children[1];
            if (dialog_el.Children[2].IsVisible == true){ // if its a text
                dialog_el = dialog_el.Children[2].Children[0].Children[2].Children[0].Children[0];
                el.text = dialog_el.TextNoTags;
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
            // var el_rect = GameController.IngameState.IngameUi.NpcDialog.GetClientRect();
            el.screen_zone = getListOfIntFromElRect(GameController.IngameState.IngameUi.NpcDialog);

            if (GameController.IngameState.IngameUi.NpcDialog.NpcLineWrapper.ChildCount != 0){
                foreach (var choice_element in GameController.IngameState.IngameUi.NpcDialog.NpcLineWrapper.Children){
                    elements_to_iterate.Add(choice_element);
                }
            } else {
                // 1 2 0 0 2 .TextNoTags
                el.text = GameController.IngameState.IngameUi.NpcDialog.GetChildAtIndex(1)?.GetChildAtIndex(2)?.GetChildAtIndex(0)?.GetChildAtIndex(0)?.GetChildAtIndex(2)?.TextNoTags;
            }
            var dialog_el = GameController.IngameState.IngameUi.NpcDialog.Children[0];
        } else {
            var reward_ui = getNpcRewardUi();
            if (reward_ui.visible != 0){
                el.screen_zone = reward_ui.screen_zone;
                el.reward_choices = reward_ui.choices;
            } else {
                el.is_visible = 0;
            }
        }
        if (elements_to_iterate.Count != 0){
            foreach (var choice_element in elements_to_iterate){
                if (choice_element.ChildCount != 0){
                    NpcDialogueUiChoice_c npc_dialogue_choice = new NpcDialogueUiChoice_c();
                    npc_dialogue_choice.text = choice_element.Children[0].TextNoTags;
                    // var el_rect = choice_element.GetClientRect();
                    npc_dialogue_choice.screen_zone = getListOfIntFromElRect(choice_element);
                    el.choices.Add(npc_dialogue_choice);
                }
            }
        }

        return el;
    }
    public NpcRewardUi_c getNpcRewardUi(){
        NpcRewardUi_c el = new NpcRewardUi_c();
        el.choices = new List<InventoryObjectCustom_c>();
        el.visible = GameController.IngameState.IngameUi.QuestRewardWindow.IsVisible ? 1 : 0;
        if (el.visible != 0){
            var el_rect = GameController.IngameState.IngameUi.QuestRewardWindow.GetClientRect(); // label_element_rect
            el.screen_zone = new List<int> {
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
                item.screen_zone = new List<int> {
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
    public MapUi_c getMapInfo(){
        MapUi_c el = new MapUi_c();
        el.is_visible = GameController.IngameState.IngameUi.Map.IsVisible ? 1 : 0;
        el.text_elements = new List<BlueLine_c>();

        foreach (var blue_line in GameController.IngameState.IngameUi.Map.BlueWords.Children[0].Children){
            BlueLine_c blue_line_obj = new BlueLine_c();
            var el_rect = blue_line.GetClientRect();
            blue_line_obj.screen_zone = new List<int> {
                (int)el_rect.X, 
                (int)(el_rect.X + el_rect.Width), 
                (int)el_rect.Y, 
                (int)(el_rect.Y + el_rect.Height), 
            };
            blue_line_obj.text = blue_line.TextNoTags;
            blue_line_obj.is_visible = blue_line.IsVisibleLocal ? 1 : 0;
            el.text_elements.Add(blue_line_obj);
        }
        return el;
    }
    public WorldMapUI_c getWorldMapUi(){
        WorldMapUI_c el = new WorldMapUI_c();
        el.is_visible = GameController.IngameState.IngameUi.WorldMap.IsVisible ? 1 : 0;
        var el_rect = GameController.IngameState.IngameUi.WorldMap.GetClientRect(); // label_element_rect
        el.screen_zone = new List<int> {
            (int)el_rect.X, 
            (int)(el_rect.X + el_rect.Width), 
            (int)el_rect.Y, 
            (int)(el_rect.Y + el_rect.Height), 
        };
        return el;
    }
    public PartyInfo_c getPartyInfo(){
        PartyInfo_c el = new PartyInfo_c();
        el.party_members = new List<PartyMember_c>();
        if (GameController.IngameState.IngameUi.PartyElement.IsVisible == false){
            return el;
        }
        var party_leader_social_element = GameController.IngameState.IngameUi.SocialPanel.GetChildFromIndices([2,0,5,1,2,0,1,0,1,0,1,0,0,0,1,0,0,0]);
        string party_leader_ign = "asd";
        if (party_leader_social_element != null){
            party_leader_ign = party_leader_social_element.Text;
        }
        DebugWindow.LogMsg($"party_leader_ign {party_leader_ign}");
        foreach (var party_member_row in GameController.IngameState.IngameUi.PartyElement.Children[0].Children){
            PartyMember_c party_el = new PartyMember_c();
            party_el.ign = party_member_row.GetChildFromIndices([0,0]).Text;
            party_el.is_leader = (party_leader_ign == party_el.ign);
            party_el.area_raw_name = party_member_row.GetChildFromIndices([2]).Text;
            party_el.screen_zone = getListOfIntFromElRect(party_member_row);
            el.party_members.Add(party_el); 
        }
        return el;
    }
    public int? getEntityIdByPlayerName(string player_name){
        int? player_id = null;
        foreach (var entity in GameController.EntityListWrapper.Entities){
            var entity_player_component = entity.GetComponent<Player>();
            if (entity_player_component != null){
                if (entity_player_component.PlayerName == player_name){
                    return (int)entity.Id;
                }
            }
        }
        return player_id;
    }
    public UltimatumNextWaveUi getUltimatumNextWaveUi(){
        UltimatumNextWaveUi el = new UltimatumNextWaveUi();
        var ultimatum_next_wave_ui_element = GameController.IngameState.IngameUi.Root.Children[1].Children[99];
        el.is_visible = ultimatum_next_wave_ui_element.IsVisible ? 1 : 0;
        if (el.is_visible == 1){
            try {
                var el_rect = ultimatum_next_wave_ui_element.GetClientRect(); // label_element_rect
                el.screen_zone = new List<int> {
                    (int)el_rect.X, 
                    (int)(el_rect.X + el_rect.Width), 
                    (int)el_rect.Y, 
                    (int)(el_rect.Y + el_rect.Height), 
                };
                var round_text = ultimatum_next_wave_ui_element.Children[0].Children[3].Text;
                el.round = round_text;
                // ultimatum choices
                el.choices = new List<string>();
                var ultimatum_choices = ultimatum_next_wave_ui_element.Children[2].Children[4].Children[0].Children;
                foreach (var child_element in ultimatum_choices){
                    var text = "???";
                    try {
                        var child_element_nested = child_element.Tooltip.Children[1].Children[3]; 
                        text = child_element_nested.Text;
                    }  catch (Exception ex){
                        DebugWindow.LogMsg($"getvisible lables ultimatum next window choices {ex}");
                    }
                    el.choices.Add(text);
                }
                var ch_el_rect = ultimatum_next_wave_ui_element.Children[2].Children[4].Children[0].GetClientRect(); // label_element_rect
                el.choices_label_screen_zone = new List<int> {
                    (int)ch_el_rect.X, 
                    (int)(ch_el_rect.X + ch_el_rect.Width), 
                    (int)ch_el_rect.Y, 
                    (int)(ch_el_rect.Y + ch_el_rect.Height), 
                };
                var visible_text = ultimatum_next_wave_ui_element.Children[2].Children[6].Children[0].Children[1].IsVisible ? "visible" : "not_visible" ;
                el.is_trial_chosen = visible_text;

            }  catch (Exception ex){
                DebugWindow.LogMsg($"getUltimatumNextWaveUi {ex}");
            }
        }
        return el;
    }
    public AnointUi_c getAnointUi(){
        AnointUi_c el = new AnointUi_c();
        el.is_visible = GameController.IngameState.IngameUi.AnointingWindow.IsVisible ? 1 : 0;
        if (el.is_visible == 0){
            return el;
        }
        var anoint_panel = GameController.IngameState.IngameUi.AnointingWindow.Children[GameController.IngameState.IngameUi.AnointingWindow.Children.Count-1];
        el.screen_zone = getListOfIntFromElRect(anoint_panel);

        el.oils = new List<InventoryObjectCustom_c>();
        var oils_element = anoint_panel.GetChildAtIndex(4);
        if (oils_element != null){
            foreach (var item_parent in oils_element.Children){
                var item_element = item_parent.GetChildFromIndices([0,1]);
                if (item_element != null){
                    var item_obj = convertItem(item_element.Entity);
                    item_obj.screen_zone = getListOfIntFromElRect(item_element);
                    el.oils.Add(item_obj);
                }
            }
        }
        
        el.placed_items = new List<InventoryObjectCustom_c>();
        var placed_item_element = anoint_panel.GetChildFromIndices([6,1]);
        if (placed_item_element != null){
            var item_obj = convertItem(placed_item_element.Entity);
            item_obj.screen_zone = getListOfIntFromElRect(placed_item_element);
            el.placed_items.Add(item_obj);
        }
        
        var anoint_button_element = anoint_panel.GetChildAtIndex(5);
        el.annoint_button_screen_zone = getListOfIntFromElRect(anoint_button_element);

        el.texts = new List<string>();
        var texts_element = anoint_panel.GetChildAtIndex(3);
        if (texts_element != null){
            if (texts_element.Children[1].IsVisible == true){
                el.texts.Add(texts_element.Children[1].TextNoTags);
            } else if (texts_element.Children[2].TextNoTags != null){
                el.texts.Add(texts_element.Children[2].TextNoTags);

            }
        }
        return el;
    }
    public ResurrectUi_c getResurrectUi(){
        ResurrectUi_c el = new ResurrectUi_c();
        el.is_visible = GameController.IngameState.IngameUi.ResurrectPanel.IsVisible ? 1 : 0;
        var el_rect = GameController.IngameState.IngameUi.ResurrectPanel.GetClientRect(); // label_element_rect
        el.screen_zone = new List<int> {
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
            visible_label.greed_position = new List<int> {
                (int)label.ItemOnGround.GridPos.X,
                (int)label.ItemOnGround.GridPos.Y
            };
            var label_element = label.Label; 
            // screen zone
            // var label_element_rect = label_element.GetClientRect(); // label_element_rect
            visible_label.displayed_name = label_element.TextNoTags;
            visible_label.screen_zone = getListOfIntFromElRect(label_element);
            var world_item_component = label.ItemOnGround.GetComponent<WorldItem>();
            if (world_item_component != null){
                var item_entity = world_item_component.ItemEntity;
                // icon?
                var render_item_component = item_entity.GetComponent<RenderItem>();
                if (render_item_component != null){
                    visible_label.animated_property_metadata = render_item_component.ResourcePath;
                }
                // // sockets
                // var sockets_component = item_entity.GetComponent<Sockets>();
                // if (sockets_component != null){
                //     visible_label.l = sockets_component.SocketGroup;
                // }
                // mods
                var mods_component = item_entity.GetComponent<Mods>();
                if (mods_component != null){
                    visible_label.rarity = mods_component.ItemRarity.ToString();
                }

                visible_label.is_targetable = 0;
                visible_label.is_targeted = 0;
                var targetable_comp = label.ItemOnGround.GetComponent<Targetable>();
                if (targetable_comp != null){
                    visible_label.is_targetable = targetable_comp.isTargetable ? 1 : 0;
                    visible_label.is_targeted = targetable_comp.isTargeted ? 1 : 0;
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
                    visible_label.item_metadata = animated_component.BaseAnimatedObjectEntity.Path;
                }
            // ultimatum start window
            } else if (label.ItemOnGround.Path == "Metadata/Terrain/Leagues/Ultimatum/Objects/UltimatumChallengeInteractable") {
                try {

                    visible_label.is_visible = label_element.Children[0].IsVisible ? 1 : 0;
                    visible_label.path = label.ItemOnGround.Path;
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
                    visible_label.screen_zone = new List<int> { 
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
                    visible_label.is_visible = label_element.Children[0].IsVisible ? 1 : 0;
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

                    atlar_label.path = label.ItemOnGround.Path;
                    atlar_label.id = (int)label.ItemOnGround.Id;
            
                    atlar_label.p_o_s = new Posx1x2y1y2();
                    atlar_label.p_o_s.x1 = (int)altar_element.GetClientRect().X;
                    atlar_label.p_o_s.x2 = (int)(altar_element.GetClientRect().X + altar_element.GetClientRect().Width);
                    atlar_label.p_o_s.y1 = (int)altar_element.GetClientRect().Y;
                    atlar_label.p_o_s.y2 = (int)(altar_element.GetClientRect().Y + altar_element.GetClientRect().Height);
                    visible_labels.Add(atlar_label);
                }
                continue;
             } else if (label.ItemOnGround.Path == "Metadata/Terrain/Gallows/Leagues/Delirium/Act1Town/Objects/DeliriumnatorAct1") {
                VisibleLabel deli_activator_label = new VisibleLabel();
                deli_activator_label.texts = new List<string>();
                var texts_parent_element = label.Label.GetChildAtIndex(0);
                if (texts_parent_element != null){
                    foreach (var item in texts_parent_element.Children){
                        if (item.Text != null){
                            deli_activator_label.texts.Add(item.Text);                        
                        }
                    }
                }
                deli_activator_label.path = label.ItemOnGround.Path;
                deli_activator_label.id = (int)label.ItemOnGround.Id;
                deli_activator_label.screen_zone = getListOfIntFromElRect(label.Label);
                visible_labels.Add(deli_activator_label);
                continue;
             } else if (label.ItemOnGround.Path == "Metadata/Terrain/Leagues/Necropolis/Objects/NecropolisCorpseMarker") {
                VisibleLabel necropolis_label = new VisibleLabel();
                necropolis_label.texts = new List<string>();

                necropolis_label.path = label.ItemOnGround.Path;
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

            visible_label.path = label.ItemOnGround.Path;
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
            entity.id = (int)obj.Id;
            entity.path = obj.Path;
            entity.grid_position = new List<int> { (int)obj.GridPos.X, (int)obj.GridPos.Y };
            entity.world_position = new List<int> { (int)obj.BoundsCenterPos.X,(int)obj.BoundsCenterPos.Y,(int)obj.BoundsCenterPos.Z };
            // entity_type
            entity.entity_type = serializeEntityType(obj.Type.ToString());
            // BoundsCenterPos
            // need for checking if item is collectable
            try {
                if ((int)obj.BoundsCenterPos.X != 0){
                    entity.bound_center_pos = 1;
                } else {
                    entity.bound_center_pos = 0;
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
                } else if (entity.entity_type == "wi") {
                    continue;
                }

                entity.location_on_screen = new List<int> { loc_on_screen_x, loc_on_screen_y };
            }
            catch (Exception e){
                DebugWindow.LogMsg($"getVisibleLabelOnGroundEntities -> {e}");
            }

            // render name # need only for area transitions
            entity.render_name = obj.RenderName;

            // is_targetable
            try {
                entity.is_targetable = obj.IsTargetable ? 1 : 0;
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
        player_info.buffs = new List<string>();
        player_info.grid_position = new List<int>{
            (int)GameController.EntityListWrapper.Player.GridPos.X,
            (int)GameController.EntityListWrapper.Player.GridPos.Y
        };
        player_info.life_component = new List<int> { 
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
            player_info.buffs.Add(buff.Name);
        }
        var player_comp  = GameController.Game.IngameState.Data.LocalPlayer.GetComponent<Player>();
        if (player_comp != null){
            player_info.lvl = player_comp.Level;
        };
        var player_actor_comp  = GameController.Game.IngameState.Data.LocalPlayer.GetComponent<Actor>();
        if (player_actor_comp != null){
            player_info.is_moving = player_actor_comp.isMoving ? 1 : 0;
        };
        return player_info;
    }
    public SkillsOnBar_c getSkillBar(bool detailed = false){
        SkillsOnBar_c skill_bars = new SkillsOnBar_c();
        skill_bars.can_be_used = new List<int>();
        skill_bars.casts_per_100_seconds = new List<int>();
        skill_bars.total_uses = new List<int>();
        skill_bars.internal_name = new List<string>();
        skill_bars.descriptions = new List<List<Dictionary<string, int>>>();
        foreach (var skill_bar_element in GameController.IngameState.IngameUi.SkillBar.Skills){
            ActorSkill skill_element = skill_bar_element.Skill;
            int can_be_used = 0;
            if (skill_element.CanBeUsed == true){
                can_be_used = 1;
            }
            skill_bars.can_be_used.Add(can_be_used);
            skill_bars.casts_per_100_seconds.Add(skill_element.HundredTimesAttacksPerSecond);
            skill_bars.total_uses.Add(skill_element.TotalUses);
            if (detailed == true){
                skill_bars.internal_name.Add(skill_element.InternalName);
                var stats_list = new List<Dictionary<string, int>>(); 
                foreach (var skill_stat in skill_element.Stats){
                    stats_list.Add(new Dictionary<string, int>{{skill_stat.Key.ToString(), skill_stat.Value}});
                }
                skill_bars.descriptions.Add(stats_list);
            }
        }
        return skill_bars;
    }
    public FlasksOnBar getFlasksInfo(bool detailed = true){
        FlasksOnBar flasks_info = new FlasksOnBar();
        flasks_info.can_use_flask = new List<int>();
        flasks_info.flask_indexes = new List<int>();
        flasks_info.flask_base_names = new List<string>();

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
                    flasks_info.can_use_flask.Add(can_use);
                    flasks_info.flask_indexes.Add((int)flask_item.InventoryPosition.X);
                    flasks_info.flask_base_names.Add(item.GetComponent<Base>().Name);
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
        converted_item.item_mods_raw = new List<string>();
        
        converted_item.is_corrupted = 0;
        if (orig_item.GetComponent<Base>().isCorrupted == true){
            converted_item.is_corrupted = 1;
        }

        Stack stack_component = orig_item.GetComponent<Stack>();
        converted_item.items_in_stack = 0;
        if (stack_component != null){
            converted_item.items_in_stack = stack_component.Size;
        }
        
        var map_component = orig_item.GetComponent<ExileCore2.PoEMemory.Components.Map>();
        converted_item.map_tier = 0;
        if (map_component != null){
            converted_item.map_tier = map_component.Tier;
        }

        // icon?
        var render_item_component = orig_item.GetComponent<RenderItem>();
        if (render_item_component != null){
            converted_item.a = render_item_component.ResourcePath;
        }

        // var sockets_component = orig_item.GetComponent<Sockets>();
        // if (sockets_component != null){
        //     converted_item.l = sockets_component.SocketGroup;
        // }

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
                converted_item.item_mods_raw.Add(mod.RawName);
            }
            converted_item.is_identified = 0;
            if (mods_component.Identified == true){
                converted_item.is_identified = 1;
            }
        }

        return converted_item;
    }
    public GetMapDeviceInfoObject mapDeviceInfo(){
        GetMapDeviceInfoObject map_device_info = new GetMapDeviceInfoObject();
        var atlas_panel_object = GameController.IngameState.IngameUi.WorldMap.AtlasPanel;
        map_device_info.atlas_panel_opened = GameController.IngameState.IngameUi.WorldMap.IsVisible;
        map_device_info.world_map_opened = atlas_panel_object.IsVisible;
        if (atlas_panel_object.IsVisible == false){
            return map_device_info;
        }


        List<WorldMapEndGameMapObj> avaliable_maps  = new List<WorldMapEndGameMapObj>();
        var maps = atlas_panel_object.Descriptions;
        foreach (var tile in maps){
            var mapElement = tile.Element;
            bool can_run = false;
            if ((mapElement.IsUnlocked == false && mapElement.IsVisited == true) || (mapElement.IsUnlocked == true && mapElement.IsVisited == false)){
                can_run = true;
            }
            // if (can_run == false){
            //     continue;
            // }
            WorldMapEndGameMapObj map_obj = new WorldMapEndGameMapObj();
            map_obj.name = mapElement.Area.Name;
            map_obj.name_raw = mapElement.Area.Id;
            // map_obj.id = mapElement.Area.Index;
            map_obj.id = (int)mapElement.IndexInParent;
            
            map_obj.can_run = can_run ? 1 : 0;

            var el_rect = mapElement.GetClientRect();
            map_obj.screen_zone = new List<int> {
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
        map_device_info.availiable_maps = avaliable_maps;

        // place map window
        var world_map_object = GameController.IngameState.IngameUi.WorldMap;
        int world_map_children_count = world_map_object.Children.Count;

        // int running_iter = world_map_children_count - 2;
        // while (running_iter < world_map_children_count){
        for (int running_iter = world_map_children_count - 2; running_iter < world_map_children_count; running_iter++){
            var child_element = world_map_object.Children[running_iter];
            if (child_element.Children.Count == 3){
                var place_map_window_element = child_element;
                map_device_info.place_map_window_is_opened = place_map_window_element.IsVisible;
                if (place_map_window_element.IsVisible == false){
                    break;
                }

                var placemapwindowelementrectangle = place_map_window_element.GetClientRect();
                map_device_info.place_map_window_screen_zone = new List<int> {
                    (int)placemapwindowelementrectangle.X, 
                    (int)(placemapwindowelementrectangle.X + placemapwindowelementrectangle.Width), 
                    (int)placemapwindowelementrectangle.Y, 
                    (int)(placemapwindowelementrectangle.Y + placemapwindowelementrectangle.Height), 
                };

                var activatebuttonreactangle = place_map_window_element.Children[1].Children[6].Children[1].GetClientRect();
                map_device_info.place_map_window_activate_button_screen_zone = new List<int> {
                    (int)activatebuttonreactangle.X, 
                    (int)(activatebuttonreactangle.X + activatebuttonreactangle.Width), 
                    (int)activatebuttonreactangle.Y, 
                    (int)(activatebuttonreactangle.Y + activatebuttonreactangle.Height), 
                };

                map_device_info.place_map_window_text = place_map_window_element.Children[1].Children[0].Text;



                var items_placed_in_map_device_parent = place_map_window_element.Children[1].Children[6].Children[0];
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
                        item.screen_zone = new List<int> {
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
                map_device_info.placed_items = items;

                break;
            }
            // running_iter += 1;
        }

        // 0 6 579 0
        var ziggurat_button_parent_element = GameController.IngameState.IngameUi.WorldMap.GetChildFromIndices([0,6]);
        for (int running_iter = ziggurat_button_parent_element.Children.Count - 2; running_iter < ziggurat_button_parent_element.Children.Count; running_iter++){
            var child_element = ziggurat_button_parent_element.Children[running_iter];
            if (child_element.TextureName == "Art/Textures/Interface/2D/2DArt/UIImages/InGame/AtlasScreen/AtlasPlayerLocationBg.dds"){
                map_device_info.ziggurat_button_screen_zones = getListOfIntFromElRect(child_element);
                break;
            }
        }
        map_device_info.realmgate_screenzones = new List<List<int>>();
        var all_map_elements = GameController.IngameState.IngameUi.WorldMap.AtlasPanel.Children;
        foreach (var map_el in all_map_elements){
            if (map_el.Height == 70 && map_el.Width == 90 && map_el.Children.Count == 1){
                var map_el_child = map_el.Children[0];
                if (map_el_child.X == 45 && map_el_child.Y == 5){
                    map_device_info.realmgate_screenzones.Add(getListOfIntFromElRect(map_el));
                    // break;
                }
            } 
        }
        // height width == 70 90
        // and it has single child with X  == 45, y == 5


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

    public GetDataObject getData(string type){
        GetDataObject response = new GetDataObject();
        DebugWindow.LogMsg("call getData");
        bool detailed = false;
        if (type == "full"){
            detailed = true;
        }
        try{
            // game state
            response.game_state = 0; 
            if (GameController.Game.IsInGameState == true){
                response.game_state = 20;
            } else if (GameController.Game.IsLoginState == true){
                response.game_state = 1;
            } else if (GameController.Game.IsSelectCharacterState){
                response.game_state = 10;
            }

            // window related
            // window pos
            var window = GameController.Window.GetWindowRectangleTimeCache;
            response.window_borders = new List<int> {
                (int)window.BottomLeft.X, 
                (int)window.TopRight.X, 
                (int)window.TopRight.Y, 
                (int)window.BottomLeft.Y, 
            };
            response.mouse_cursor_pos = new List<int> {
                (int)GameController.IngameState.MousePosX, 
                (int)GameController.IngameState.MousePosY, 
            };

            // area related
            // response.IsLoading = GameController.Game.IsLoading;
            response.IsLoading = !GameController.IngameState.InGame;
            response.invites_panel_visible = false;
            var loading_panel = GameController.IngameState.IngameUi.GetChildAtIndex(108);
            if (loading_panel != null){
                response.invites_panel_visible = loading_panel.IsVisible;
            }
            // response.ipv = GameController.IngameState.IngameUi.InvitesPanel.IsVisible;
            response.IsLoading_b = false;

            foreach (var game_state in GameController.Game.ActiveGameStates){
                // [-4:] 6220 - escape menu
                // [-4:] 5620 - loading

                string game_state_str = $"{game_state.Address:X}";
                string lastFourDigits = game_state_str.Substring(game_state_str.Length - 4);
                // DebugWindow.LogMsg($"checking full {game_state_str}");
                if (lastFourDigits == "5620"){
                    response.IsLoading_b = true;
                    break;
                }
            }
            response.area_raw_name = GameController.Area.CurrentArea.Area.Id;
            response.area_hash = GameController.Area.CurrentArea.Hash;

            response.player_info = getPlayerInfo();
            response.awake_entities = getAwakeEntities();
            response.item_labels = getItemsOnGroundLabelsVisible();
            response.visible_labels = getVisibleLabelOnGroundEntities();
            response.skills = getSkillBar(detailed);
            response.flasks = getFlasksInfo();
        } catch (Exception e) {
            DebugWindow.LogError($"ShareData cannot build player data -> {e}");
        }
        if (detailed == true) {
            response.terrain_string = generateMinimap().ToString();
            response.controller_type = GameController.Game.InputType.GetHashCode();
        }
        DebugWindow.LogMsg("return getData");
        return response;

    }
    private string ProcessRequest(string rawRequest)
    {
        DebugWindow.LogMsg($"Received request: {rawRequest}");
        try
        {
            string path = rawRequest.Split('?')[0];
            string query = rawRequest.Contains('?') ? rawRequest.Split('?')[1] : "";

            switch (path)
            {
                case "/getData":
                    string requestType = ExtractQueryParameter(query, "type", "partial");

                    if (requestType == "full"){
                        return SerializeData(getData(requestType));
                    } else {
                        // Thread-safe access to the last item in the list
                        string data;
                        lock (dataTempLock)
                        {
                            data = data_cache[data_cache.Count - 1];
                            // if (data_cache.Count > 0)
                            // {
                            // }
                        }
                        return data;

                    }


                    // return SerializeData(getData(requestType));

                case "/getLocationOnScreen":
                    int x = int.Parse(ExtractQueryParameter(query, "x"));
                    int y = int.Parse(ExtractQueryParameter(query, "y"));
                    int z = int.Parse(ExtractQueryParameter(query, "z"));
                    var screenCoord = GameController.IngameState.Camera.WorldToScreen(new System.Numerics.Vector3(x, y, z));
                    return SerializeData(new List<int> { (int)screenCoord.X, (int)screenCoord.Y });

                case "/getScreenPos":
                    int sx = int.Parse(ExtractQueryParameter(query, "x"));
                    int sy = int.Parse(ExtractQueryParameter(query, "y"));
                    return SerializeData(getScreenPos(sx, sy));

                case "/getInventoryInfo":
                    return SerializeData(getInventoryInfo());

                case "/getOpenedStashInfo":
                    return SerializeData(getStashInfo());

                case "/getVisibleLabelOnGroundEntities":
                    return SerializeData(getVisibleLabelOnGroundEntities());

                case "/getItemsOnGroundLabelsVisible":
                    return SerializeData(getItemsOnGroundLabelsVisible());

                case "/mapDeviceInfo":
                    return SerializeData(mapDeviceInfo());

                case "/getAtlasProgress":
                    return SerializeData(getAtlasProgress());

                case "/getVisibleLabels":
                    return SerializeData(getVisibleLabels());

                case "/getHoveredItemInfo":
                    return SerializeData(getHoveredItemInfo());

                case "/getSkillBar":
                    return SerializeData(getSkillBar(true));

                case "/getLabTrialsState":
                    return SerializeData(GameController.IngameState.IngameUi.GetQuests);

                case "/getQuestStates":
                    return SerializeData(getQuestStates());

                case "/getWaypointsState":
                    return SerializeData(GameController.IngameState.Data.ServerData.WaypointsUnlockState);

                case "/getMinimapIcons":
                    return SerializeData(getMinimapIcons());

                case "/getRitualUi":
                    return SerializeData(getRitualUi());

                case "/getWorldMapUi":
                    return SerializeData(getWorldMapUi());

                case "/getUltimatumNextWaveUi":
                    return SerializeData(getUltimatumNextWaveUi());

                case "/getResurrectUi":
                    return SerializeData(getResurrectUi());

                case "/getPurchaseWindowHideoutUi":
                    return SerializeData(getPurchaseWindowHideoutUi());

                case "/getQuestFlags":
                    return SerializeData(GameController.IngameState.Data.ServerData.QuestFlags);

                case "/getPreloadedFiles":
                    return SerializeData(getPreloadedFiles());

                case "/getAuctionHouseUi":
                    return SerializeData(getAuctionHouseUi());

                case "/ForceRefreshArea":
                    GameController.Area.ForceRefreshArea();
                    return SerializeData("ForceRefreshArea_OK");

                case "/getMapInfo":
                    return SerializeData(getMapInfo());

                case "/getAnointUi":
                    return SerializeData(getAnointUi());

                case "/getEntityIdByPlayerName":
                    string playerName = ExtractQueryParameter(query, "type");
                    return SerializeData(getEntityIdByPlayerName(playerName));

                case "/getPartyInfo":
                    return SerializeData(getPartyInfo());

                case "/getNpcDialogueUi":
                    return SerializeData(getNpcDialogueUi());

                case "/getNpcRewardUi":
                    return SerializeData(getNpcRewardUi());

                default:
                    return "Unknown request";
            }
        }
        catch (Exception ex)
        {
            DebugWindow.LogError($"ProcessRequest error: {ex}");
            return "Error processing request";
        }
    }

    private string ExtractQueryParameter(string query, string key, string defaultValue = "")
    {
        var parameters = query.Split('&');
        foreach (var param in parameters)
        {
            var keyValue = param.Split('=');
            if (keyValue.Length == 2 && keyValue[0] == key)
            {
                return keyValue[1];
            }
        }
        return defaultValue;
    }

    private string SerializeData(object data)
    {
        return Newtonsoft.Json.JsonConvert.SerializeObject(data, Newtonsoft.Json.Formatting.None);
    }
}

