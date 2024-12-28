from ast import literal_eval

class Config:
    def __init__(self, cli_args=None, *, prefer_high_tier=True, 
                 alch_map_if_possible=True, max_map_lvl=15,
                 rares_detection_radius=999):
        self._default_config = {
            "REMOTE_IP": '192.168.50.182',  # z2
            "unique_id": "poe_2_test",
            "build": "EaBallistasEle",
            "password": None,
            "max_lvl": 101,
            "chromatics_recipe": True,
            "force_reset_temp": False,
            "prefer_high_tier": prefer_high_tier,
            "max_map_lvl": max_map_lvl,
            "alch_map_if_possible": alch_map_if_possible,
            "rares_detection_radius": rares_detection_radius,
        }
        
        self._config = self._init_config(cli_args)
    
    def _init_config(self, cli_args):
        try:
            if cli_args:
                parsed_config = literal_eval(cli_args)
                print('successfully parsed cli config')
                print(f'parsed_config: {parsed_config}')
            else:
                print('cannot parse config from cli, using default config')
                parsed_config = self._default_config
        except:
            print('cannot parse config from cli, using default config')
            parsed_config = self._default_config

        config = {}
        for key in self._default_config.keys():
            config[key] = parsed_config.get(key, self._default_config[key])

        print(f'config to run {config}')
        return config

    @property
    def remote_ip(self):
        return self._config['REMOTE_IP']

    @property
    def unique_id(self):
        return self._config['unique_id']

    @property
    def max_lvl(self):
        return self._config['max_lvl']

    @property
    def chromatics_recipe(self):
        return self._config['chromatics_recipe']

    @property
    def build_name(self):
        return self._config['build']

    @property
    def password(self):
        return self._config['password']

    @property
    def force_reset_temp(self):
        return self._config['force_reset_temp']

    @property
    def prefer_high_tier(self):
        return self._config['prefer_high_tier']

    @property
    def alch_map_if_possible(self):
        return self._config['alch_map_if_possible'] 

    @property
    def max_map_lvl(self):
        return self._config['max_map_lvl']

    @property
    def rares_detection_radius(self):
        return self._config['rares_detection_radius']
