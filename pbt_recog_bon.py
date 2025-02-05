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


TEMP=0.7

def generate_recog_prompt(problem: Dict[str,Any]) -> str:
        return f"""You are given a coding problem description, and a formal specification of the requirements in Lean 4.
You are also given a candidate solution to the problem,
and outputs from a property-based testing procedure that checks the output of the candidate solution given random inputs against the specifications.

If the property-based testing indicates there are failed test cases, determine why the tests failed, and try to fix the errors in the candidate
solution.

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
{problem.get('property_def', '')}

{problem['theorem_signature']}

{problem.get('theorem2_signature', '')}
```
The candidate solution:
```
{problem['code_solution']}
```
Outputs from the property-based testing procedure, indicating the input-output values from the candidate solution that failed to satisfy the specification:
{problem['pbt_results']}

You are encouraged to think step by step. You do not need to prove the theorem statements.
Use the provided tool to further test your modified Lean code on the input values that the original solution failed on. 
Iterate until your code produces correct outputs for those inputs.
You may further test your code on other inputs as well.
"""


async def solve_recog (problem: Dict[str, Any], model='sonnet', max_attempts=10):
    prompt = generate_recog_prompt(problem)
    res=await interactive_lean_check(prompt, model=models[model], max_attempts=max_attempts,temperature=TEMP)

    print (res)
    out=''
    for att in res['attempts']:
        out+='\nAttempt:\n'
        if 'thought' in att: out+=str(att.get('thought',''))+'\n'
        out+=att.get('code','')+'\n'
        out+=str(att.get('result',''))

    if out=='': out=res['messages'][-1]['content']
    print (out)
    ret={'output':out}
    if 'final_code' in res:
        lt=tester.LeanTester()
        _,output,stats=lt.test_solution(res['final_code'], problem)
        print(output)
        print(stats)
        ret['output']+='\n'+ res['final_code']
        ret['tests_passed']=stats['passed']
        ret['tests_total']=stats['total']

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
        print ('using model', model)
        if len(sys.argv)>4:
          max_att=sys.argv[4]
        else:
          max_att=3
        inp_jo=copy.deepcopy(jo)
        if 'statement' in jo:
          inp_jo['description']=jo['statement']
        else:
          inp_jo['description']=jo['description']
        #print (json.dumps(inp_jo,indent=4))
        try:
          for attempts in range(max_att):
            solution=await solve_recog(inp_jo, model=model)
            if solution.get('tests_total',0)>0 and solution['tests_passed']==solution['tests_total']:
              break
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
