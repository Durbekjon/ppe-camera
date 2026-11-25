"""List the globals a torch .pt checkpoint's pickle would import, without unpickling it."""
import pickletools, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
name = next(n for n in z.namelist() if n.endswith("data.pkl"))
mods = set()
strs = []
for op, arg, _ in pickletools.genops(z.read(name)):
    if op.name == "GLOBAL":
        mods.add(arg.replace(" ", "."))
    elif op.name in ("BINUNICODE", "SHORT_BINUNICODE", "UNICODE"):
        strs.append(arg)
    elif op.name == "STACK_GLOBAL":
        mods.add(".".join(strs[-2:]))
roots = sorted({m.split(".")[0] for m in mods})
print("root modules:", roots)
print("non-torch/ultralytics:", sorted(m for m in mods if m.split(".")[0] not in ("torch", "ultralytics", "collections", "numpy")))
