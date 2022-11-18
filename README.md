# src/geometrics
A python module with some helpful tools for 3d design

## Prepare
```
Make sure you have the latest versions of:
  - https://github.com/pypa/build
  - https://github.com/pypa/installer
  - https://github.com/pypa/hatch
  and
  - all the dependencies listed in pyproject.toml 
```

## Build
From the root of this repo
```
rm -rf buildout && python -m build --wheel --no-isolation --outdir buildout
```

## Install
choose one of:
### Install in a venv (recommended)
These instructions are for Linux, but working with virtual environments should be very similar on all platforms. See https://docs.python.org/3/library/venv.html#creating-virtual-environments
```
python -m venv ~/venvs/geometrics --clear --system-site-packages --without-pip
source ~/venvs/geometrics/bin/activate
python -m installer buildout/*.whl
rm -r buildout

deactivate  # when you're done with the venv
```
### Install without a venv
See https://docs.python.org/3/library/sysconfig.html?highlight=installation%20scheme#installation-paths for valid schemas and pick one that's appropriate for your use case
```
python -m uninstaller --scheme posix_user geometrics
python -m installer --scheme posix_user buildout/*.whl
```

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
