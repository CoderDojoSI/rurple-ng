import distutils.core 
import py2exe

distutils.core.setup(
    options = {
        "py2exe": {
            "dll_excludes": ["MSVCP90.dll"]
        }
    },

    windows = ["start_rurple.py"],
    packages = ["rurple", "rurple.worlds"]
)
