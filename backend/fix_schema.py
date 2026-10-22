import re

with open('prisma/schema.prisma', 'r') as f:
    content = f.read()

content = re.sub(r'String\s+String\s+@default\(VIEWER\)', r'role String @default(\"VIEWER\")', content)
content = re.sub(r'status\s+String\s+@default\(PENDING\)', r'status String @default(\"PENDING\")', content)
content = re.sub(r'status\s+String\s+@default\(OPEN\)', r'status String @default(\"OPEN\")', content)
content = re.sub(r'String\s+String\n\s+status\s+String\s+@default\(\"OPEN\"\)', r'severity String\n  status String @default(\"OPEN\")', content)
content = re.sub(r'String\s+String', r'severity String', content)

with open('prisma/schema.prisma', 'w') as f:
    f.write(content)
