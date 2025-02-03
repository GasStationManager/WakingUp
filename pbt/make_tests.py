import re
import subprocess
import json
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
import asyncio
import copy
import traceback


@dataclass
class TestInput:
    name: str
    type_name: str
    values: List[str]


def extract_imports(code: str):
    lines=code.splitlines(keepends=True)
    imports=''
    rest=''
    for ln in lines:
        if ln.startswith('import'):
            imports+=ln
        else:
            rest+=ln
    return imports, rest


class MakeTester:
    def __init__(self, spec: Dict[str, str], sol_fname: str):
        self.description = spec['description']
        self.function_signature = spec['function_signature']
        with open(sol_fname) as f:
          self.code_solution = f.read()

    def extract_input_types(self) -> List[TestInput]:
        """Extract input parameter types from function signature."""
        # First split the signature into parameter groups
        param_groups = re.findall(r'\(([^)]+)\)', self.function_signature)
        
        inputs = []
        for group in param_groups:
            # Check if it's a grouped declaration (multiple names sharing one type)
            if ':' in group:
                names_str, type_name = group.split(':', 1)
                # Split names while handling both space-separated and comma-separated formats
                names = [n.strip() for n in re.split(r'[,\s]+', names_str) if n.strip()]
                type_name = type_name.strip()
                
                # Create an input entry for each name with the shared type
                for name in names:
                    inputs.append(TestInput(name=name,
                                         type_name=type_name,
                                         values=[]))
                                         
        return inputs

    def generate_sample_script(self, type_name: str) -> str:
        """Generate Lean script to sample given type."""
        return f"""
import Plausible

#sample {type_name}
        """

    def generate_eval_script(self, inputs: List[str]) -> str:
        """Generate Lean script to evaluate function with given inputs."""
        input_params = " ".join(f"{inp}" for inp in inputs)
        imports,rest=extract_imports(self.code_solution)
        return f"""
{imports}
set_option linter.unusedVariables false

{rest}

#eval {self.function_signature.split('(')[0].strip().replace('def', '')} {input_params}
        """

    def run_lean_script(self, script: str) -> str:
        """Run Lean script and return output using a temporary file."""
        import tempfile
        import os
        
        # Create temporary file with .lean extension
        with tempfile.NamedTemporaryFile(suffix='.lean', mode='w', delete=False) as temp_file:
            temp_file.write(script)
            temp_path = temp_file.name
            
        try:
            # Run Lean and capture output
            result = subprocess.run(['lake','env','lean', temp_path], 
                                  capture_output=True,
                                  text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Lean script failed:\nscript:\n{script}\n{result.stdout}\n{result.stderr}\n")
                
            return result.stdout
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Handle cleanup errors silently


    async def run_tests(self, num_tests: int = 20) -> Dict[str, Any]:
        """Run property-based tests."""
        results = []

        input_types = self.extract_input_types()

        
        for input_param in input_types:
            sample_script = self.generate_sample_script(input_param.type_name)
            while len(input_param.values)< num_tests:
              try:
                sample_output = self.run_lean_script(sample_script)
                input_param.values += ['('+v+')' for v in sample_output.strip().splitlines()]
              except RuntimeError as e:
                if 'failed to synthesize' in str(e) or 'unknown identifier' in str(e):
                  input_param.values += ['(by decide)'] * num_tests
                else: raise e
        inputs_set=set()
        for test_num in range(num_tests):
            #inputs
            inputs = [inp.values[test_num] for inp in input_types]
            inpstr=' '.join(inputs)
            if inpstr in inputs_set:
              print(inpstr, 'already added')
              continue
            else:
              inputs_set.add(inpstr)
            # Evaluate function
            eval_script = self.generate_eval_script(inputs)
            try:
              output = self.run_lean_script(eval_script).strip().splitlines()
              output = ['' if 'warning' in ln else ln for ln in output]
              output='\n'.join(output).strip()
              print('input', inputs, 'output', output)
              results.append({
                'input': ' '.join(inputs),
                'output': output
              })
            except RuntimeError as e:
              print (e)
        print('number of tests generated: ', len(results))
        return results

async def run_make_tests(spec: Dict[str, str], sol_fname: str) -> Dict[str, Any]:
    tester = MakeTester(spec, sol_fname)
    try:
        res = await tester.run_tests()
    except RuntimeError as e:
        print(e)
        res=[]
    return res

async def main():
    import jsonlines
    fn=sys.argv[1]
    sol_fn=sys.argv[2]
    outfn=sys.argv[3]
    with jsonlines.open(fn) as reader:
      with jsonlines.open(outfn, mode='w') as writer:
        for jo in reader:
            res=await run_make_tests(jo, sol_fn)
            print (res)
            out_jo=copy.deepcopy(jo)
            out_jo['tests']=res
            writer.write(out_jo)

if __name__=='__main__':
    asyncio.run(main())
