using ExileCore2.Shared.Nodes;
using ExileCore2.Shared.Interfaces;

namespace ShareData
{
    public class ShareDataSettings : ISettings
    {
        public ShareDataSettings()
        {
            Enable = new ToggleNode(true);
        }
        public ToggleNode Enable { get; set; }
    }
}
