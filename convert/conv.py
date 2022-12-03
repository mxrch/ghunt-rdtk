from pathlib import Path
from typing import *
import re
import hashlib
from glob import glob
import json

import inflection


initial_values = {
    "str": '""',
    "int": "0",
    "float": "0.0",
    "dict": "{}",
    "list": "[]",
    "bool": "False",
}

def extract_json(raw: str):
    splited = raw.split("{")
    if len(splited) <= 1:
        return False
    rebuilt = "{" + '{'.join(splited[1:])

    data = ""
    try:
        data = json.loads(rebuilt)
    except:
        return False
    return data

class Value():
    def __init__(self):
        self.type: str = ""
        self.list_of: str = ""

class Model():
    def __init__(self):
        self.is_parent: bool = False
        self.keys_type: str = "str"
        self.values_type: str = "str"
        self.args: Dict[str, Value] = {}

def calculate_dict_hash(data: Dict) -> str:
    txt = ""
    for key in sorted(data.keys()):
        txt += f"${key}"
    for value in [type(x).__name__ for x in data.values()]:
        txt += f"@{value}"
    return hashlib.md5(txt.encode()).hexdigest()

def parse(data, name="", first=False):
    global unknown_model_count

    if isinstance(data, dict) and data:
        name = inflection.camelize(name)
        if "kind" in data:
            name = ''.join([inflection.camelize(x) for x in data["kind"].split("#")])
        elif first:
            name = "BaseModel"
        elif not name:
            hash = calculate_dict_hash(data)
            if hash not in unknown_cache:
                unknown_cache[hash] = unknown_model_count
                unknown_model_count += 1
            name = f"UnknownModel{unknown_cache[hash]}"

        first = False
        
        if not name.startswith(prefix):
            name = inflection.camelize(prefix+name)
        if name not in known_models:
            model = Model()
            known_models[name] = model

        keys_type = type(list(data.keys())[0]).__name__
        values_type = type(list(data.values())[0]).__name__
        is_parent = False
        for key, val in data.items():
            new_key_type = type(key).__name__
            new_val_type = type(val).__name__

            if isinstance(key, str) and key.isnumeric():
                key = "digits_field"

            known_models[name].args[key] = Value()

            type_of_list, new_name = parse(val, key)
            if new_val_type == "dict":
                if new_name:
                    new_val_type = new_name
                is_parent = True
            elif new_val_type == "list":
                known_models[name].args[key].list_of = type_of_list

            known_models[name].args[key].type = new_val_type

            if new_key_type != keys_type:
                keys_type = "any"
            if new_val_type != values_type:
                values_type = "any"

        known_models[name].keys_type = keys_type
        known_models[name].values_type = values_type
        known_models[name].is_parent = is_parent
    elif isinstance(data, list) and data:
        fetched_models = set()
        first = False
        for item in data:
            typeof, new_name = parse(item)
            if not new_name:
                new_name = typeof
            fetched_models.add(new_name)
        if len(fetched_models) > 1:
            return "any", name
        else:
            return list(fetched_models)[0], name

    return type(data).__name__, name

def output():
    out = "from typing import *\nfrom ghunt.objects.apis import Parser\n\n\n"
    for name, model in known_models.items():
        out += f"class {name}(Parser):\n"
        out += "\tdef __init__(self):\n"
        for key, val in model.args.items():
            field_name = inflection.underscore("".join([ch for ch in key if ch.isalpha()]))
            if val.type in initial_values:
                if val.type == "list":
                    out += f"\t\tself.{field_name}: List[{val.list_of}] = {initial_values[val.type]}\n"
                else:
                    out += f"\t\tself.{field_name}: {val.type} = {initial_values[val.type]}\n"
            else:
                out += f"\t\tself.{field_name}: {val.type} = {val.type}()\n"
        out += "\n"

        data_name = re.sub(f"^{prefix.lower()}_", "", inflection.underscore(name))
        data_fullname = f"{data_name}_data"
        out += f"\tdef _scrape(self, {data_fullname}: Dict[{model.keys_type}, {model.values_type}]):\n"
        for key, val in model.args.items():
            field_name = inflection.underscore("".join([ch for ch in key if ch.isalpha()]))
            if val.type in initial_values and not (val.type == "list" and (val.list_of not in initial_values)):
                out += f"\t\tself.{field_name} = {data_fullname}.get('{key}')\n"
            else:
                child_data_name = field_name
                child_data_fullname = f"{child_data_name}_data"
                child_data_item = f"{child_data_name}_data_item"
                child_item = f"{child_data_name}_item"
                if val.type == "list":
                    out += f"\t\tif ({child_data_fullname} := {data_fullname}.get('{key}')):\n"
                    out += f"\t\t\tfor {child_data_item} in {child_data_fullname}:\n"
                    out += f"\t\t\t\t{child_item} = {val.list_of}()\n"
                    out += f"\t\t\t\t{child_item}._scrape({child_data_item})\n"
                    out += f"\t\t\t\tself.{child_data_name}.append({child_item})\n"
                else:
                    out += f"\t\tif ({child_data_fullname} := {data_fullname}.get('{key}')):\n"
                    out += f"\t\t\tself.{child_data_name}._scrape({child_data_fullname})\n"

        out += "\n"

    with open(f"convert/generated/{prefix.lower()}_autogenerated.py", "w", encoding="utf8") as f:
        f.write(out)

folders = glob("convert/jsons/*")
for folder in folders:
    prefix = Path(folder).name
    known_models: Dict[str, Model] = {}
    unknown_cache: Dict[str, int] = {}
    unknown_model_count = 1
    datas = []
    files = glob(f"{folder}/*")
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            data = extract_json(f.read())
            if data:
                datas.append(data)

    for item in datas:
        parse(item, first=True)
    output()