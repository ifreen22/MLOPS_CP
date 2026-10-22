const fs = require('fs');
const path = require('path');

function replace(file, search, replace) {
  const p = path.join(__dirname, 'src', file);
  if (fs.existsSync(p)) {
    const content = fs.readFileSync(p, 'utf8');
    fs.writeFileSync(p, content.replace(search, replace));
  }
}

replace('components/Layout.tsx', "import React, { ReactNode } from 'react';", "import React from 'react';\nimport type { ReactNode } from 'react';");
replace('components/layout/AppLayout.tsx', "import { Link, ", "import { ");
replace('features/root-cause/CustomNode.tsx', "import React, ", "import ");
replace('features/root-cause/CustomNode.tsx', "const ringColor", "// const ringColor");
replace('features/root-cause/RootCauseGraph.tsx', "import { Node, Edge, NodeChange, EdgeChange, ", "import type { Node, Edge, NodeChange, EdgeChange } from '@xyflow/react';\nimport { ");
replace('features/root-cause/RootCauseGraph.tsx', "nds =>", "(nds: any) =>");
replace('features/root-cause/RootCauseGraph.tsx', "eds =>", "(eds: any) =>");
replace('features/situations/SituationRoom.tsx', "import React, ", "import ");
replace('features/situations/SituationRoom.tsx', "const colors =", "// const colors =");
replace('features/situations/SituationRoom.tsx', "event =>", "(event: any) =>");
replace('features/situations/SituationRoom.tsx', "(svc, i)", "(svc: any, i: any)");
replace('features/situations/SituationRoom.tsx', "(alert, i)", "(alert: any, i: any)");

// Also we need to fix api.ts by adding the missing types.
const apiTs = path.join(__dirname, 'src', 'services', 'api.ts');
if (fs.existsSync(apiTs)) {
  let content = fs.readFileSync(apiTs, 'utf8');
  content = content.replace("updatedAt: z.string(),", "updatedAt: z.string(),\n  rootCause: z.any().optional(),\n  alerts: z.any().optional(),\n  chronology: z.any().optional(),");
  fs.writeFileSync(apiTs, content);
}

console.log("Fixes applied.");
