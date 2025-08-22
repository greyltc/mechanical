# src/geometrics
A python module with some helpful tools for 3d design

## Development workflow
1) Use git to clone this repo and cd into its folder
1) Install dependancies system-wide using your favorite python package manager. You could view those like this:
    ```bash
    hatch project metadata | jq -r '.dependencies | .[]'
    ```
    also install python's build[1], installer[2] and wheel[3] packages
1) Setup a clean virtual environment for development/testing
    ```bash
    python -m venv --without-pip --system-site-packages --clear venv
    ```
1) Prepare an editable wheel
   ```bash
   python -c 'import build; print(build.ProjectBuilder(".").build("editable", "venv"))'
   ```
1) Activate the venv (see [4] for alternative non-linux/bash instructions)
    ```bash
    source venv/bin/activate
    ```
1) Install the editable wheel into the venv
    ```bash
    python -m installer venv/*.whl
    ```
1) Develop! When you're finished with it, you can deactivate the virtual environment with `deactivate`

[1]: https://build.pypa.io/en/stable/
[2]: https://installer.pypa.io/en/stable/
[3]: https://wheel.readthedocs.io/en/stable/
[4]: https://docs.python.org/3/library/venv.html#how-venvs-work


## Some folders
### chamber_ng/
next generation substrate holder

### scratch_tool/
unit to guide scratching utensils

### lim_chamber/
chamber for Jong

### lightsource/
lightsource mockup

### sandwich/
older device holder sandwich stackup

### groovy/
o-ring grooves

### badger/
badger project

### otter/
otter project
