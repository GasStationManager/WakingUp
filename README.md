# WakingUp: Experiments on Hallucination Detection and Recovery

[Writeup on the initial experiment](https://gasstationmanager.github.io/ai/2025/01/22/hallucination.html)

[Writeup on followup experiments](https://gasstationmanager.github.io/ai/2025/02/05/hallucination-followup.html)

## Installation

- install Lean 4
- install poetry
- clone repository
- cd into the repo, then clone [LeanTool](https://github.com/GasStationManager/LeanTool)
- install LeanTool by following its instructions, which includes installing Pantograph
- modify `pyproject.toml` in this directory (WakingUp) to have the right path name for pantograph's wheel file
- `poetry install`
- `lake update`
- cd pbt
- `lake update` (unfortunately, the scripts in `pbt` directory have a dependence on a different version of mathlib, so we are installing two versions of mathlib in two different directories)


## Pipeline

- `code_contests_sample_passed.jsonl`: 10 autoformalized problem instances, created from `code_contests` data set via the FormalizeWithTest pipeline.
- `easy_with_tests.jsonl`: CodeProofBenchmark problems, with test cases automatically generated using the script `pbt/make_tests.py`
- in the repo directory, do
```
poetry shell
```
- To test an AI model in code-only mode:
```
python code_only.py code_contests_sample_passed.jsonl <output_file> <model_name>
```
where model_name can be gpt (for GPT 4o), sonnet (for Sonnet 3.5), and deepseek (for DeepSeek v3). You can try any other model supported by LiteLLM.
- Manually inspect the outputs. In our initial experiment, we focused on a particular problem where DeepSeek passed 3 out of 4 test cases. 
Extract the lines (e.g. using grep) for further processing.
- To apply PBT:
```
cd pbt
python pbt.py ../<input_file> ../<output_file>
```
- To prompt the model to correct the code given PBT results:
```
cd ..
python pbt_recog.py <input_file> <output_file> <model_name>
``` 

## Episodes

Examples of hallucination detection and recovery are collected in the directory `episodes/`.
