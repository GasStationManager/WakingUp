import re
import subprocess
import json
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
import asyncio
import copy
import traceback
import verify


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


class PropertyBasedTester:
    def __init__(self, spec: Dict[str, str]):
        self.description = spec['description']
        self.function_signature = spec['function_signature']
        self.property_name = spec.get('property_name')
        self.property_def = spec.get('property_def')
        self.code_solution = spec['code_solution']
        self.theorem_signature=spec.get('theorem_signature')
        self.theorem2_signature=spec.get('theorem2_signature', '')
        
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
                raise RuntimeError(f"Lean script failed: {result.stdout}\n{result.stderr}\nscript:\n{script}")
                
            return result.stdout
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Handle cleanup errors silently

    async def verify_property(self, inputs: List[str], output: str) -> str:
        """Call external verifier to check if property holds."""
        # Create verification context
        context = {
            'prop_def': self.property_def,
            'prop_name': self.property_name,
            'test_case': ' '.join([inp for inp in inputs]) + ' ' + output
        }
        
        # Call external verifier (placeholder)
        result = await verify.verify(**context)
        print(result)
        return result['status']



    def gen_plausible_script(self, theorem_sig:str):
        code=self.code_solution.replace('def', '@[simp] def')
        script=f"""
import Plausible

{code}

{theorem_sig} := by
  simp
  plausible
"""
        return script
    def run_plausible_script(self, theorem_sig:str):
        success=True
        try:
            r=self.run_lean_script(self.gen_plausible_script(theorem_sig))
        except RuntimeError as e:
            r=str(e)
            if 'error: Failed to create' in r:
                success=False
        return success,r

    def try_plausible(self):
        output=''
        success,r=self.run_plausible_script(self.theorem_signature)
        if success:
            output+=f"Result of running plausible on the theorem statement {self.theorem_signature}:\n"
            output+=r
        else:
            print (f'Plausible failed for {self.theorem_signature}:', r)
        if len(self.theorem2_signature.strip())>0:
            success,r=self.run_plausible_script(self.theorem2_signature)
            if success:
                output+=f"\nResult of running plausible on the theorem statement {self.theorem2_signature}:\n"
                output+=r
            else:
                print(f'Plausible failed for {self.theorem2_signature}:',r)
        return output

    async def run_tests(self, num_tests: int = 100) -> Dict[str, Any]:
        """Run property-based tests."""
        if self.property_def is None:
            return {'output': self.try_plausible()} 
        results = {
            'total_tests': num_tests,
            'passed': 0,
            'unknown': 0,
            'failed': 0,
            'failures': []
        }

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
        for test_num in range(num_tests):
            #inputs
            inputs = [inp.values[test_num] for inp in input_types]
            # Evaluate function
            eval_script = self.generate_eval_script(inputs)
            try:
              output = self.run_lean_script(eval_script).strip().splitlines()
              output = ['' if 'warning' in ln else ln for ln in output]
              output='\n'.join(output).strip()
              # Verify property
              r = await self.verify_property(inputs, output)
            except RuntimeError as e:
              print (e)
              r = 'unknown'
            if r=='pass':
                results['passed'] += 1
            elif r=='unknown':
                results['unknown'] += 1
            else:
                results['failed'] += 1
                results['failures'].append({
                    'inputs': {inp.name: inp.values[test_num] for inp in input_types},
                    'output': output
                })
                
        return results

async def run_property_testing(spec: Dict[str, str]) -> Dict[str, Any]:
    """Main entry point for property-based testing."""
    tester = PropertyBasedTester(spec)
    return await tester.run_tests()


async def main():
    import jsonlines
    fn=sys.argv[1]
    outfn=sys.argv[2]
    with jsonlines.open(fn) as reader:
      with jsonlines.open(outfn, mode='w') as writer:
        for jo in reader:
            res=await run_property_testing(jo)
            print (res)
            out_jo=copy.deepcopy(jo)
            out_jo['pbt_results']=res
            writer.write(out_jo)

if __name__=='__main__':
    asyncio.run(main())
