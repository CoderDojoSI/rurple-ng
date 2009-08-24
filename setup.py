import distutils.core 
import py2exe

distutils.core.setup(
    options = {
        "py2exe": {
            "dll_excludes": ["MSVCP90.dll"],
            "dist_dir": "build/Rurple",
        }
    },
    windows = [{
        "script": "start_rurple.py",
        "dest_base": "rurple",
    }],
    packages = ["rurple", "rurple.worlds"]
)
