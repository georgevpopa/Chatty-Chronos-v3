import sys
import json
import traceback
import io
from RestrictedPython import compile_restricted
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import safe_builtins, guarded_iter_unpack_sequence

# Sandbox setup using RestrictedPython
_REPL_GLOBALS = {
    '__builtins__': safe_builtins,
    '_getiter_': default_guarded_getiter,
    '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
    '_getattr_': getattr, 
    '_getitem_': lambda obj, key: obj[key],
    '_write_': lambda obj: obj,
}

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            req = json.loads(line)
            code = req.get("code", "")
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            redirected = io.StringIO()
            sys.stdout = redirected
            sys.stderr = redirected
            
            try:
                # Compile restricted code
                compiled = compile_restricted(code, "<string>", "exec")
                exec(compiled, _REPL_GLOBALS)
            except Exception:
                traceback.print_exc(file=sys.stdout)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
            out = redirected.getvalue().strip()
            if not out:
                out = "(Code executed successfully. No output generated.)"
                
            resp = {"status": "success", "output": out}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            sys.stdout.write(json.dumps({"status": "error", "output": str(e)}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
