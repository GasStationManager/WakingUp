# WakingUp: Experiments on Hallucination Detection and Recovery

[Writeup on the initial experiment](https://gasstationmanager.github.io/ai/2025/01/22/hallucination.html)


## Installation
- install Lean 4
- install poetry
- clone repository
- cd into the repo, then clone [LeanTool](https://github.com/GasStationManager/LeanTool)
- install LeanTool by following its instructions, which includes installing Pantograph
- modify pyproject.toml in this directory (WakingUp) to have the right path name for pantograph's wheel file
- `poetry install`
- `lake update`
- cd pbt
- `lake update` (unfortunately, the scripts in `pbt` directory have a dependence on a different version of mathlib, so we are installing two versions of mathlib in two different directories)

