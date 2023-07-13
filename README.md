# src/geometrics
A python module with some helpful tools for 3d design

## Development workflow
1) Use git to clone this repo and cd into its folder
1) Install dependancies system-wide using your favorite python package manager. View those like this:
    ```bash
    $ hatch project metadata | jq -r '.dependencies | .[]'
    ```
1) Setup a virtual environment for development/testing
    ```bash
    $ python -m venv --without-pip --system-site-packages --clear venv
    ```
1) Activate the venv (this step is os/shell-dependant, see [1] for non-linux/bash)
    ```bash
    $ source venv/bin/activate
    ```
1) Install the package in editable mode into the venv
    ```bash
    (venv) $ python tools/venv_dev_install.py
    ```
1) Develop! When you're finished with it, you can deactivate the virtual environment with `deactivate`

[1]: https://docs.python.org/3/library/venv.html#how-venvs-work


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
