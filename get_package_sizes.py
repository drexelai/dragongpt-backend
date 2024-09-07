import os
import sys
from pip._internal.operations.freeze import freeze

## This code is used to get the size of the packages that are installed in the backend/venv

def get_package_size(package_name):
    try:
        package_location = next(
            p.split("==")[0] for p in freeze() if p.startswith(package_name)
        )
        package_location = os.path.join(sys.prefix, "Lib", "site-packages", package_name)
        if os.path.isdir(package_location):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(package_location):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            return total_size
        return 0
    except StopIteration:
        return 0

packages = sorted(
    [(p.split("==")[0], get_package_size(p.split("==")[0])) for p in freeze()],
    key=lambda x: x[1],
    reverse=True,
)

for package_name, size in packages:
    print(f"{package_name} {size / (1024 * 1024):.2f} MB")
