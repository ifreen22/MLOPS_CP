import re
import os

prisma_path = r"c:\Users\Ifreen\Downloads\MLOPS_CP\backend\prisma\schema.prisma"
backend_dir = r"c:\Users\Ifreen\Downloads\MLOPS_CP\backend\app"

with open(prisma_path, "r") as f:
    content = f.read()

models = re.findall(r"model\s+(\w+)\s+{([^}]+)}", content)
enums = re.findall(r"enum\s+(\w+)\s+{([^}]+)}", content)

schema_code = ["from pydantic import BaseModel, ConfigDict", "from typing import Optional, List, Any", "from datetime import datetime", "from enum import Enum", ""]

for enum_name, enum_values in enums:
    schema_code.append(f"class {enum_name}(str, Enum):")
    for val in enum_values.strip().split("\n"):
        val = val.strip()
        if val:
            schema_code.append(f"    {val} = '{val}'")
    schema_code.append("")

for model_name, model_body in models:
    fields = []
    lines = model_body.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        parts = re.split(r'\s+', line)
        if len(parts) >= 2:
            field_name = parts[0]
            field_type_raw = parts[1]
            if "[]" in field_type_raw:
                continue # skip relations for base schema simplicity initially
            if "@relation" in line:
                continue # skip relations
            
            is_optional = "?" in field_type_raw
            field_type = field_type_raw.replace("?", "")
            
            py_type = "str"
            if field_type == "String": py_type = "str"
            elif field_type == "Int": py_type = "int"
            elif field_type == "Float": py_type = "float"
            elif field_type == "Boolean": py_type = "bool"
            elif field_type == "DateTime": py_type = "datetime"
            elif field_type == "Json": py_type = "Any"
            else: py_type = field_type # Enum
            
            if is_optional:
                py_type = f"Optional[{py_type}]"
            
            fields.append((field_name, py_type, is_optional))
            
    # Base
    schema_code.append(f"class {model_name}Base(BaseModel):")
    for fname, ftype, is_opt in fields:
        if fname not in ["id", "createdAt", "updatedAt"]:
            if is_opt:
                schema_code.append(f"    {fname}: {ftype} = None")
            else:
                schema_code.append(f"    {fname}: {ftype}")
    if len(fields) <= 3:
        schema_code.append("    pass")
    schema_code.append("")

    # Create
    schema_code.append(f"class {model_name}Create({model_name}Base):")
    schema_code.append("    pass")
    schema_code.append("")

    # Update
    schema_code.append(f"class {model_name}Update(BaseModel):")
    has_update_fields = False
    for fname, ftype, is_opt in fields:
        if fname not in ["id", "createdAt", "updatedAt"]:
            schema_code.append(f"    {fname}: Optional[{ftype.replace('Optional[', '').replace(']', '')}] = None")
            has_update_fields = True
    if not has_update_fields:
        schema_code.append("    pass")
    schema_code.append("")

    # Response
    schema_code.append(f"class {model_name}Response({model_name}Base):")
    for fname, ftype, is_opt in fields:
        if fname in ["id", "createdAt", "updatedAt"]:
            schema_code.append(f"    {fname}: {ftype}")
    schema_code.append("    model_config = ConfigDict(from_attributes=True)")
    schema_code.append("")

with open(os.path.join(backend_dir, "schemas", "all_schemas.py"), "w") as f:
    f.write("\n".join(schema_code))

print("Schemas generated.")

# Now generate services and controllers
router_code = ["from fastapi import APIRouter"]
router_includes = []

for model_name, _ in models:
    lower_name = model_name.lower()
    
    # Service
    service_code = f'''from typing import List, Optional
from app.schemas.all_schemas import {model_name}Create, {model_name}Update
from app.core.db import prisma

class {model_name}Service:
    @staticmethod
    async def create(data: {model_name}Create):
        return await prisma.{lower_name}.create(data=data.model_dump(exclude_unset=True))

    @staticmethod
    async def get(id: str):
        return await prisma.{lower_name}.find_unique(where={{"id": id}})

    @staticmethod
    async def get_all(skip: int = 0, limit: int = 100):
        return await prisma.{lower_name}.find_many(skip=skip, take=limit)

    @staticmethod
    async def update(id: str, data: {model_name}Update):
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await prisma.{lower_name}.find_unique(where={{"id": id}})
        return await prisma.{lower_name}.update(where={{"id": id}}, data=update_data)

    @staticmethod
    async def delete(id: str):
        return await prisma.{lower_name}.delete(where={{"id": id}})
'''
    with open(os.path.join(backend_dir, "services", f"{lower_name}_service.py"), "w") as f:
        f.write(service_code)
        
    # Controller
    controller_code = f'''from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.all_schemas import {model_name}Create, {model_name}Update, {model_name}Response
from app.services.{lower_name}_service import {model_name}Service

router = APIRouter(prefix="/{lower_name}s", tags=["{model_name}s"])

@router.post("/", response_model={model_name}Response)
async def create_{lower_name}(data: {model_name}Create):
    return await {model_name}Service.create(data)

@router.get("/", response_model=List[{model_name}Response])
async def get_{lower_name}s(skip: int = 0, limit: int = 100):
    return await {model_name}Service.get_all(skip, limit)

@router.get("/{{id}}", response_model={model_name}Response)
async def get_{lower_name}(id: str):
    item = await {model_name}Service.get(id)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return item

@router.put("/{{id}}", response_model={model_name}Response)
async def update_{lower_name}(id: str, data: {model_name}Update):
    item = await {model_name}Service.update(id, data)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return item

@router.delete("/{{id}}")
async def delete_{lower_name}(id: str):
    item = await {model_name}Service.delete(id)
    if not item:
        raise HTTPException(status_code=404, detail="{model_name} not found")
    return {{"message": "{model_name} deleted successfully"}}
'''
    with open(os.path.join(backend_dir, "api", "v1", "controllers", f"{lower_name}_controller.py"), "w") as f:
        f.write(controller_code)
        
    router_code.append(f"from app.api.v1.controllers.{lower_name}_controller import router as {lower_name}_router")
    router_includes.append(f"api_router.include_router({lower_name}_router)")

router_code.append("")
router_code.append("api_router = APIRouter()")
router_code.extend(router_includes)

with open(os.path.join(backend_dir, "api", "v1", "router.py"), "w") as f:
    f.write("\\n".join(router_code).replace('\\n', '\n'))

print("Controllers and services generated.")
