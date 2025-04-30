

from datasets import load_dataset
import sys


def get_fsig(example):
    lines=example['spec'].splitlines()
    sig=''
    for ln in lines:
        if ln.strip().startswith('def'):
          fname=ln.strip().split('def')[1].split('(')[0].strip()
          if fname in example['units']:
            sig=ln.strip().split(':=')[0]
            break
    example['function_signature']=sig
    return example

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("quinn-dougherty/fvapps",cache_dir="datasets",split='train')
ds = ds.filter(lambda x: x['assurance_level']=='guarded_and_plausible' and x['units'] and str(x['units']).strip()!='')
ds=ds.rename_column('apps_question', 'description')
ds=ds.map(get_fsig)
ds=ds.filter(lambda x: x['function_signature'].strip()!='')
ds.to_json(sys.argv[1])
