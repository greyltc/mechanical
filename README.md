# src/geometrics
A python module with some helpful tools for 3d design

## Build
From the root of this repo, requires https://github.com/pypa/build
```
python -m build --outdir .buildwork
#python -m build --no-isolation --outdir buildout
```

## Install & Use Locally
After building, from the root of this repo, requires https://github.com/pypa/installer
### With venv
```
python -m venv ~/venvs/geometrics --clear --system-site-packages --without-pip
source ~/venvs/geometrics/bin/activate  # or however venvs are activated on your platform, see https://docs.python.org/3/library/venv.html#creating-virtual-environments
python -m installer .buildwork/*.whl
rm -rf /tmp/dummy
rm -rf .buildwork

deactivate  # when you're done with the venv
```
### With .local
```
python -m installer --destdir /tmp/dummy .buildwork/*.whl
cp -a /tmp/dummy/usr/* ~/.local/.
rm -rf /tmp/dummy
rm -rf .buildwork
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
