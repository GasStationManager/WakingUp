import asyncio
import time
import traceback
import sys
import jsonlines
from typing import List, Dict, Any
from dataclasses import dataclass
import copy
from LeanTool.leantool import interactive_lean_check, models
import tester




def generate_recog_prompt(problem: Dict[str,Any]) -> str:
        return f"""You are given a coding problem description, and a formal specification of the requirements in Lean 4.
You are also given a candidate solution to the problem. Determine whether the candidate solution satisfies the formal specification.

Problem Description:
```
{problem['description']}
```
The Lean 4 function should have the following signature:
```
{problem['function_signature']}
```
The formal specification:
```
{problem['property_def']}

{problem['theorem_signature']}
```
The candidate solution:
```
{problem['code_solution']}
```

One suggestion to find counterexamples: try plugging in input values and then try to prove the negation of the theorem statement.
"""


async def solve_recog (problem: Dict[str, Any], model='sonnet'):
    prompt = generate_recog_prompt(problem)
    res=await interactive_lean_check(prompt, model=models[model])

    ret=res['messages'][-1]['content']
    print (ret)
    return ret


async def main():
  with jsonlines.open(sys.argv[1]) as f:
    with jsonlines.open(sys.argv[2], mode='w') as fout:
      for jo in f:
        await asyncio.sleep(1)
        if len(sys.argv)>3:
          model=sys.argv[3]
        else:
          model='sonnet'
        inp_jo=copy.deepcopy(jo)
        if 'statement' in jo:
          inp_jo['description']=jo['statement']
        else:
          inp_jo['description']=jo['description']
        #print (json.dumps(inp_jo,indent=4))
        try:
          solution=await solve_recog(inp_jo, model=model)
          out_jo=copy.deepcopy(inp_jo)
          out_jo['recog_solution']=solution
        except Exception as e:
          print ('Error:')
          print (e)
          traceback.print_exc()
          continue
        if not out_jo: continue
        #print(json.dumps(out_jo,indent=4))
        fout.write(out_jo)


if __name__=='__main__':
    asyncio.run(main())
