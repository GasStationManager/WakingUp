import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any
import re
import traceback

class LeanTester:
    def __init__(self):
        """Initialize the tester."""
        pass

    def create_test_file(self, implementation: str, problem: Dict[str, Any]) -> str:
        """Create a temporary Lean file with the implementation and test cases."""
        test_template = """
{implementation}

def main : IO Unit := do
  {test_assertions}
  IO.println s!"Tests passed: {passed_count}/{total_count}"
where
  checkEqual (a b : {result_type}) : IO Bool := do
    if a == b then
      IO.println "Test passed"
      pure true
    else
      IO.println s!"Test failed: expected {{b}} but got {{a}}"
      pure false
"""
        # Process the implementation to remove any existing main function
        implementation = re.sub(r'def\s+main.*?end', '', implementation, flags=re.DOTALL)
        
        # Extract function information from the signature
        signature_match = re.search(r'def\s+(\w+)\s*\((.*?)\)\s*:\s*([^:=]+)', problem['function_signature'])
        if not signature_match:
            raise ValueError(f"Could not parse function signature: {problem['function_signature']}")
        
        fn_name = signature_match.group(1)
        params = signature_match.group(2)
        result_type = signature_match.group(3).strip()

        # Generate test assertions
        test_assertions = []
        test_count = len(problem['tests'])
        test_assertions.append(f"let mut passed := 0")
        
        for i, test_case in enumerate(problem['tests']):
            # Split the test case into inputs and expected output
            #parts = test_case.split()
            #if len(parts) < 2:  # Need at least one input and one output
            #    raise ValueError(f"Invalid test case format: {test_case}")
            
            inputs = test_case['input']  # All but the last part are inputs
            expected = test_case['output']  # Last part is the expected output
            
            # Create the function call
            fn_call = f"{fn_name} {inputs}"
            test_assertions.append(f"""
  if ← checkEqual ({fn_call}) ({expected}) then
    passed := passed + 1""")
        
        test_assertions.append(f"\n  pure ()")

        test_content = test_template.format(
            implementation=implementation,
            test_assertions="\n  ".join(test_assertions),
            result_type=result_type,
            passed_count="{passed}",
            total_count=test_count
        )

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.lean', delete=False, mode='w') as f:
            f.write(test_content)
            print("Generated Lean file content:")
            print(test_content)
            return f.name

    def compile_and_run(self, file_path: str) -> tuple[bool, str, Dict[str, Any]]:
        """Compile and run the Lean file using lake env commands."""
        try:
            # Print file content for debugging
            with open(file_path, 'r') as f:
                print("File content:")
                code=f.read()
                print(code)
                print("\n---\n")

            # First check compilation
            compile_result = subprocess.run(
                ["lake", "env", "lean", file_path],
                capture_output=True,
                text=True
            )
            
            if compile_result.returncode != 0:
                return False, f"Compilation error:\n{compile_result.stderr}\n\nStdout:\n{compile_result.stdout}\nCode:\n{code}", {"passed": 0, "total": 0}

            # Run the program using lake env lean --run
            run_result = subprocess.run(
                ["lake", "env", "lean", "--run", file_path],
                capture_output=True,
                text=True
            )
            
            # Parse test results
            test_stats = {"passed": 0, "total": 0}
            if run_result.returncode == 0:
                # Look for the final test count line
                stats_match = re.search(r'Tests passed: (\d+)/(\d+)', run_result.stdout)
                if stats_match:
                    test_stats["passed"] = int(stats_match.group(1))
                    test_stats["total"] = int(stats_match.group(2))
            
            success = run_result.returncode == 0
            output = run_result.stdout + run_result.stderr
            print(f"\nRun output:\n{output}\n")
            return success, output, test_stats

        except Exception as e:
            return False, str(e)+'\n'+traceback.format_exc(), {"passed": 0, "total": 0}
        finally:
            # Cleanup temporary file
            try:
                os.unlink(file_path)
            except:
                pass

    def test_solution(self, implementation: str, problem: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
        """Test a solution against provided test cases."""
        if implementation is None:
            return False, 'No implementation generated', {'passed':0,'total':0}
        try:
            test_file = self.create_test_file(implementation, problem)
            return self.compile_and_run(test_file)
        except Exception as e:
            return False, str(e)+'\n'+traceback.format_exc(), {"passed": 0, "total": 0}

def process_jsonl_file(file_path: str, solution: str) -> List[Dict[str, Any]]:
    """Process a JSONL file containing test cases and evaluate the solution."""
    results = []
    tester = LeanTester()
    
    with open(file_path, 'r') as f:
        for line in f:
            problem = json.loads(line)
            success, output, stats = tester.test_solution(solution, problem)
            results.append({
                'problem_id': problem.get('id', 'unknown'),
                'success': success,
                'output': output,
                'tests_passed': stats['passed'],
                'tests_total': stats['total']
            })
    
    return results

# Example usage
if __name__ == "__main__":
    # Example solution for a generic function
    solution = """
def add (a b : Nat) : Nat :=
  a + b
"""
    
    # Example JSONL content (should be in a file)
    jsonl_content = """{"id": "test1", "function_signature": "def add (a b : Nat) : Nat", "tests": ["1 2 3", "5 3 8", "0 0 0"]}
{"id": "test2", "function_signature": "def add (a b : Nat) : Nat", "tests": ["10 20 30", "30 15 45"]}"""
    
    # Create temporary JSONL file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(jsonl_content)
        test_file = f.name

    try:
        results = process_jsonl_file(test_file, solution)
        for result in results:
            print(f"Problem {result['problem_id']}:")
            print(f"Success: {result['success']}")
            print(f"Tests passed: {result['tests_passed']}/{result['tests_total']}")
            print(f"Output: {result['output']}\n")
    finally:
        os.unlink(test_file)
