import os

base_dir = r"c:\Users\Ifreen\Downloads\MLOPS_CP\aiops-sentinel\src"

def replace_in_file(rel_path, old, new):
    filepath = os.path.join(base_dir, rel_path)
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old in content:
        content = content.replace(old, new)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Replaced in {filepath}")
    else:
        print(f"String not found in {filepath}")

replace_in_file(r"components\Layout.tsx", "import React, { ReactNode } from 'react';", "import type { ReactNode } from 'react';\nimport React from 'react';")
replace_in_file(r"components\layout\AppLayout.tsx", "import { Link, ", "import { ")
replace_in_file(r"features\root-cause\CustomNode.tsx", "import React, ", "import ")
replace_in_file(r"features\root-cause\RootCauseGraph.tsx", "import { Node, Edge, NodeChange, EdgeChange, ", "import type { Node, Edge, NodeChange, EdgeChange } from '@xyflow/react';\nimport { ")
replace_in_file(r"features\root-cause\RootCauseGraph.tsx", "nds =>", "(nds: any) =>")
replace_in_file(r"features\root-cause\RootCauseGraph.tsx", "eds =>", "(eds: any) =>")
replace_in_file(r"features\situations\SituationRoom.tsx", "event =>", "(event: any) =>")

# For the length/map property on number issue:
# In SituationRoom.tsx: Property 'length' does not exist on type 'number'.
# The user probably had `affectedServices.length` but `affectedServices` is a number in the schema!
def fix_affected_services():
    filepath = os.path.join(base_dir, r"features\situations\SituationRoom.tsx")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("situation.affectedServices.length", "situation.affectedServices")
    content = content.replace("situation.affectedServices.map", "Array.from({length: situation.affectedServices}).map")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
fix_affected_services()

print("Done")
