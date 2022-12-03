# GHunt Research & Development Toolkit

Currently, only one module is available : Autoparse.

## Autoparse
It basically takes all the JSON data you put in the `jsons` folder (one JSON structure per file, take an example on `jsons\Cac` (for ClientAuthConfig)), and it will automatically writes Python classes to parse the JSON output into Python objects, with type definition.\
The auto generated Python files will be wrote in the `generated` folder.

PS : It was made to automatically generate Python classes for GHunt's parsers, so it will import and use the parent class `ghunt.objects.apis.Parser` (which auto manages [slots](https://betterprogramming.pub/optimize-your-python-programs-for-free-with-slots-4ff4e1611d9d)) but you can easily edit the script for your needs.