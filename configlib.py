import os
import os.path

import common

def read_config(config_file_path, default_config):
        """ Read the config and update the appropriate variables. """

        def check_config(cfg, defcfg):
            """ Make sure the config is valid """
            out = {}
            for key, defvalue in defcfg.items():
                if key in cfg:
                    # We need to go deeper
                    if type(defvalue) == dict:
                        out[key] = check_config(cfg[key], defvalue)
                    # No value found, use default
                    elif not cfg[key]:
                        out[key] = defvalue
                    # Found it!
                    else:
                        out[key] = cfg[key]
                else:
                    # No key found, use default
                    out[key] = defvalue
            return out

        try:
            rawcfg = common.read_json(config_file_path)
        except (IOError, ValueError):
            print('no/bad config')
            cfg = default_config
        else:
            cfg = check_config(rawcfg, default_config)

        return cfg['settings']


def write_config(config_file_path, settings, sizepos):
        """
        Read the config, update the info with appropriate variables (optional)
        and then overwrite the old file with the updated config.
        """
        cfg = {
            'window': {
                'x': sizepos.left(),
                'y': sizepos.top(),
                'width': sizepos.width(),
                'height': sizepos.height(),
                'maximized': False,
            },
            'settings': settings
        }

        if not os.path.exists(os.path.dirname(config_file_path)):
            os.makedirs(os.path.dirname(config_file_path), mode=0o755, exist_ok=True)
            print('Creating config path...')
        common.write_json(config_file_path, cfg)

