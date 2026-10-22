import os
import subprocess

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

base_dir = r"c:\Users\Ifreen\Downloads\MLOPS_CP"
fe_dir = os.path.join(base_dir, "aiops-sentinel")

if not os.path.exists(fe_dir):
    run_cmd("npx create-vite aiops-sentinel --template react-ts", cwd=base_dir)

run_cmd("npm install", cwd=fe_dir)
deps = [
    "react-router-dom",
    "zustand",
    "@tanstack/react-query",
    "axios",
    "framer-motion",
    "recharts",
    "reactflow",
    "@monaco-editor/react",
    "socket.io-client",
    "react-hook-form",
    "zod",
    "@hookform/resolvers",
    "lucide-react",
    "clsx",
    "tailwind-merge",
]
dev_deps = [
    "tailwindcss",
    "postcss",
    "autoprefixer",
    "@types/node"
]

run_cmd(f"npm install {' '.join(deps)}", cwd=fe_dir)
run_cmd(f"npm install -D {' '.join(dev_deps)}", cwd=fe_dir)
run_cmd("npx tailwindcss init -p", cwd=fe_dir)

# Create folders
folders = [
    "src/components",
    "src/components/ui",
    "src/components/layout",
    "src/features",
    "src/features/mission-control",
    "src/features/situations",
    "src/features/alert-clustering",
    "src/features/root-cause",
    "src/features/change-intelligence",
    "src/features/playbooks",
    "src/features/slo",
    "src/features/settings",
    "src/pages",
    "src/layouts",
    "src/hooks",
    "src/services",
    "src/api",
    "src/store",
    "src/types",
    "src/utils",
    "src/constants",
    "src/routes",
    "src/assets",
    "src/styles",
    "src/contexts",
    "src/providers",
    "src/config",
]

for folder in folders:
    os.makedirs(os.path.join(fe_dir, folder), exist_ok=True)

print("Frontend setup complete!")
