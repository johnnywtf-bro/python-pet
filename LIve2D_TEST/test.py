import os
import sys

plugin_path = os.path.join(os.path.dirname(sys.executable),
                           "Lib", "site-packages", "PyQt6", "Qt", "plugins", "platforms")
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
