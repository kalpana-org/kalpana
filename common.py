class Configable():
    def init_settings_functions(self, settingsmanager):
        self.get_setting = settingsmanager.get_setting
        self.get_path = settingsmanager.get_path
        self.register_setting = lambda settingname, callback: \
                        settingsmanager.register_setting(settingname, callback)

class SettingsError(Exception):
    pass