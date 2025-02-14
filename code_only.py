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

DEBUG=True


def generate_implementation_prompt(problem: Dict[str,Any]) -> str:
        return f"""Please implement a solution to the following problem in Lean 4.
Problem Description:
{problem['description']}

The Lean 4 function should have the following signature:

{problem['function_signature']}

Make sure the implementation follows Lean 4 syntax and semantics.

Before producing the final output, use the provided tool to verify your lean code is valid.
Analyze the tool's output, if it indicates an error, identify the reason the error occurs and modify your
code. Use the tool again until there are no errors (warnings due to the sorry in the function and theorem are fi
ne). You may call the tool at most 5 times for this task.

You are encouraged to reason step by step; put your thoughts in the <Thinking> ... </Thinking> tag,
then put the final Lean 4 implementation code (including the signature) in the <Result> ... </Result> tag.
"""

async def solve_code_only (problem: Dict[str, Any], model='sonnet'):
    prompt = generate_implementation_prompt(problem)
    res=await interactive_lean_check(prompt, model=models[model], debug=DEBUG)

    if 'final_code' in res:
      ret=res['final_code']
    else:
      ret=None
    return ret


#def eval_code_only(problem:Dict[str,Any], solution: str):
#    lt=tester.LeanTester()
#    status,output,stats=lt.test_solution(solution,problem)


async def main():
  with jsonlines.open(sys.argv[1]) as f:
    with jsonlines.open(sys.argv[2], mode='w') as fout:
      lt=tester.LeanTester()
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
          solution=await solve_code_only(inp_jo, model=model)
          status,output,stats=lt.test_solution(solution,inp_jo)
          out_jo=copy.deepcopy(inp_jo)
          out_jo['code_solution']=solution
          out_jo['output']=output
          out_jo['tests_passed']=stats['passed']
          out_jo['tests_total']=stats['total']
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
