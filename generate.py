from io import StringIO
from yaml import safe_load
from typing import TypeVar, Any

enums: list[str]
classes: list[str]
typedefs: dict[str, str]
config: Any

USE_HTTPS: bool
API_URL: str

K = TypeVar('K')
V = TypeVar('V')
def reverse(theDict: dict[K, V]) -> dict[V, K]:
    return {v: k for k, v in theDict.items()}

def get_config(config_dir: str):
    with open(f'{config_dir}/generate.yaml', 'rt') as fh:
        return safe_load(fh)

def config_dict(name: str) -> dict[Any, Any]: return config.get(name, {})
def config_list(name: str) -> list[Any]: return config.get(name, [])

# this could be a decorator but long story short i spent an hour researching
# how to type annotate functions with the first argument as a string
# and the rest as generic variadics and discovered it's actually a bug
#
# https://github.com/python/mypy/issues/5876
def baseType(type: str) -> str:
    return typedefs.get(type, type)

def isExt(type: str):
    return type in reverse(config_dict('extensions'))

def extBase(type: str) -> str:
    type = baseType(type)
    return reverse(config_dict('extensions'))[type]

def mapTypes(type: str) -> tuple[str, str]:
    type = baseType(type)
    # luckily enough this just about works - the
    # only type w/ a comma in is a map, and you can't use one as a key
    comma = type.find(',')
    keyType = type[4:comma]
    valType = type[comma + 1:-1].strip()
    return keyType, valType

def generate_enum(buf: StringIO, name: str, values: dict[str, str]):
    buf.write(f'enum {name} {{\n')

    for i, value in enumerate(list(values.keys())):
        buf.write(f'  {value}')
        if i != len(values) - 1:
            buf.write(',\n')
    
    buf.write('\n}\n\n')

    buf.write(f'{name} {name}FromString(String value) => const {{\n')
    for i, value in enumerate(list(values.keys())):
        asString = values[value]
        buf.write(f"  '{asString}': {name}.{value}")
        if i != len(values) - 1:
            buf.write(',\n')
        
    buf.write('\n}[value]!;\n\n')
    
    buf.write(f'String {name}ToString({name} value) => const {{\n')
    for i, value in enumerate(list(values.keys())):
        asString = values[value]
        buf.write(f"  {name}.{value}: '{asString}'")
        if i != len(values) - 1:
            buf.write(',\n')
        
    buf.write('\n}[value]!;\n\n')

# if we're using types as keys in a Map then we need to be able to convert them to/from
# string as it's the only type JSON keys can use. because this is the only use case we only
# want to convert obvious key types.

def fromString(type: str, getter: str) -> str:
    type = baseType(type)
    if type in enums:
        return f'{type}FromString({getter})'
    elif type == 'String':
        return getter
    elif type == 'int':
        return f'int.parse({getter})'
    else:
        raise TypeError(f"Can't convert {type} to string!")

def toString(type: str, getter: str) -> str:
    type = baseType(type)
    if type in enums:
        return f'{type}ToString({getter})'
    elif type == 'String':
        return getter
    elif type == 'int':
        return f'({getter}).toString()'
    else:
        raise TypeError(f"Can't convert {type} from string!")

GENERATED_ENUMS = ['APIException', 'AuthLevel']

def fromJson(type: str, getter: str) -> str:
    type = baseType(type)
    if type.endswith('?'):
        return f'(){{ final val = {getter}; return val == null ? null : {fromJson(type[:-1], "val")}; }}()'
    elif type.startswith('List<'):
        elementFromJson = fromJson(type[5:-1], 'element')
        if elementFromJson == 'element':
            return getter
        return f'({getter} as List<dynamic>).map((element) => {elementFromJson}).toList()'
    elif type.startswith('Map<'):
        keyType, valType = mapTypes(type)
        keyFromString = fromString(keyType, 'k')
        valFromJson = fromJson(valType, 'v')
        if keyFromString == 'k' and valFromJson == 'v':
            return getter
        return f'({getter} as Map<String, dynamic>).map((k, v) => MapEntry({keyFromString}, {valFromJson}))'
    elif type in enums + GENERATED_ENUMS:
        return f'{type}.values[{getter} as int]'
    elif type in classes:
        return f'{type}.fromJson({getter})'
    elif isExt(type):
        return f'{extBase(type)}.fromJson({getter}).as{type}'
    else:
        return f'{getter} as {type}'

def toJson(type: str, getter: str) -> str:
    type = baseType(type)
    if type.endswith('?'):
        return f'(){{ final val = {getter}; return val == null ? null : {toJson(type[:-1], "val")}; }}()'
    elif type.startswith('List<'):
        elementToJson = toJson(type[5:-1], 'element')
        if elementToJson == 'element':
            return getter
        return f'{getter}.map((element) => {elementToJson}).toList()'
    elif type.startswith('Map<'):
        keyType, valType = mapTypes(type)
        keyToString = toString(keyType, 'k')
        valToJson = toJson(valType, 'v')
        if keyToString == 'k' and valToJson == 'v':
            return getter
        return f'{getter}.map((k, v) => MapEntry({keyToString}, {valToJson}))'
    elif type in enums + GENERATED_ENUMS:
        return f'{type}.values.indexOf({getter})'
    elif type in classes or isExt(type):
        return f'{getter}.toJson()'
    else:
        return getter

def generate_copywith(type: str, name: str, fields: dict[str, str], buf: StringIO):
    buf.write(f'  {type} {name}({{\n')
    for i, fieldName in enumerate(list(fields.keys())):
        fieldType = fields[fieldName]
        buf.write(f'    {fieldType}')
        if not fieldType.endswith('?'):
            buf.write('?')
        buf.write(f' {fieldName}')
        if i != len(fields) - 1:
            buf.write(',')
        buf.write('\n')
    
    buf.write(f'  }}) => {type}(\n')
    for i, fieldName in enumerate(list(fields.keys())):
        buf.write(f'    {fieldName}: {fieldName} ?? this.{fieldName}')
        if i != len(fields) - 1:
            buf.write(',')
        buf.write('\n')
    buf.write('  );\n')

def generate_base(buf: StringIO):
    global enums, classes, typedefs

    enums = list(config_dict('enums').keys())
    classes = list(config_dict('classes').keys())
    typedefs = config_dict('typedefs')

    for extension in list(config_dict('extensions').values()):
        buf.write(f"import '{extension}.dart';\n")
    
    buf.write('\n')
    buf.write(f'const kApiUseHttps = {str(USE_HTTPS).lower()};\n\n')

    for typeName, typeDef in config_dict('typedefs').items():
        buf.write(f'typedef {typeName} = {typeDef};\n')
    
    buf.write('\n')

    if 'auth' in config:
        generate_enum(buf, 'AuthLevel', {v: v for v in ['Unauthorized'] + config['auth']['levels']})
    
    for enumName, enumData in config_dict('enums').items():
        generate_enum(buf, enumName, {v: v for v in enumData})
    
    for className, classData in config_dict('classes').items():
        buf.write(f'class {className} {{\n')

        for fieldName, fieldType in classData.items():
            buf.write(f'  final {fieldType} {fieldName};\n')
        
        buf.write(f'\n  {className}({{')

        for i, fieldName in enumerate(list(classData.keys())):
            if not classData[fieldName].endswith('?'):
                buf.write('required ')
            buf.write(f'this.{fieldName}')
            if i != len(classData) - 1:
                buf.write(', ')
        
        buf.write('});\n\n')

        buf.write(f'  static {className} fromJson(Map<String, dynamic> json) => {className}(\n')

        for i, fieldName in enumerate(list(classData.keys())):
            fieldType = classData[fieldName]
            buf.write(f'    {fieldName}: ')
            buf.write(fromJson(fieldType, f"json['{fieldName}']"))
            
            if i != len(classData) - 1:
                buf.write(',\n')
            
        buf.write('\n  );\n\n')

        buf.write('  Map<String, dynamic> toJson() => {\n')
        
        for i, fieldName in enumerate(list(classData.keys())):
            fieldType = classData[fieldName]
            buf.write(f"    '{fieldName}': {toJson(fieldType, fieldName)}")
            if i != len(classData) - 1:
                buf.write(',\n')
        
        buf.write('\n  };\n\n')

        if className in config_dict('extensions'):
            extensionName = config['extensions'][className]
            buf.write(f'  {extensionName} get as{extensionName} => {extensionName}(')
            
            for i, fieldName in enumerate(list(classData.keys())):
                buf.write(f'{fieldName}: {fieldName}')
                if i != len(classData) - 1:
                    buf.write(', ')
            
            buf.write(');\n\n')

        if className in config_dict('extensions'):
            generate_copywith(className, 'copyBaseWith', classData, buf)
            buf.write('\n')
            generate_copywith(config['extensions'][className], 'copyWith', classData, buf)
        else:
            generate_copywith(className, 'copyWith', classData, buf)
        
        buf.write('}\n\n')

    exceptions = {exception.title().replace(' ', ''): exception for exception in
        ['Success', 'Unsupported method', 'Unsupported endpoint', 'Object format error', 'Internal error', 'Unauthorized'] + config_list('exceptions')
    }
    generate_enum(buf, 'APIException', exceptions)


def generate_server(buf: StringIO):
    buf.write('abstract class APIHandler {\n')
    for endpointName, endpointType in config_dict('endpoints').items():
        if endpointType.get('handledBy', 'main') != 'main': continue
        buf.write(f'  {endpointType.get("out", "void")} {endpointName}(')
        if endpointType.get('forwardToken', False):
            buf.write(f'{config["auth"]["out"]} token')
            if 'in' in endpointType:
                buf.write(', ')
        if 'in' in endpointType:
            buf.write(f'{endpointType["in"]} request')
        buf.write(');\n')
    buf.write('}\n\n')

    if 'auth' in config:
        buf.write('abstract class AuthHandler {\n')
        buf.write(f'  {config["auth"]["out"]} generateToken({config["auth"]["in"]} credentials);\n')
        buf.write(f'  AuthLevel validateToken({config["auth"]["out"]} token);\n\n')
        
        for endpointName, endpointType in config_dict('endpoints').items():
            if endpointType.get('handledBy', 'main') == 'auth':
                buf.write(f'  {endpointType.get("out", "void")} {endpointName}(')
                if endpointType.get('forwardToken', False):
                    buf.write(f'{config["auth"]["out"]} token')
                    if 'in' in endpointType:
                        buf.write(', ')
                if 'in' in endpointType:
                    buf.write(f'{endpointType["in"]} request')
                buf.write(');\n')

            if endpointType.get('authLevel', '') == 'Custom':
                buf.write(f'  bool {endpointName}Auth({config["auth"]["out"]} token')
                if 'in' in endpointType:
                    buf.write(f', {endpointType["in"]} request')
                buf.write(');\n')


        buf.write('}\n\n')
        config['endpoints']['_authorize'] = config['auth']

    buf.write('Future handleRequest(HttpRequest request, APIHandler handler, AuthHandler auth) async {\n')
    # i fucking hate web programming so much. what the fuck even is CORS
    buf.write("  request.response.headers.add('Access-Control-Allow-Origin', '*');\n")
    buf.write("  request.response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS');\n")
    buf.write("  request.response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With');\n")
    buf.write("  request.response.headers.add('Access-Control-Allow-Headers', 'Content-Type');\n")
    buf.write("  if (request.method == 'OPTIONS') {\n")
    buf.write('    request.response.close();\n')
    buf.write('    return;\n')
    buf.write("  } else if (request.method != 'POST') {\n")
    buf.write('    print("Unsupported method: \'${request.method}\'");\n')
    buf.write("    request.response.write(jsonEncode({'code': APIException.values.indexOf(APIException.UnsupportedMethod)}));\n")
    buf.write('    request.response.close();\n')
    buf.write('    return;\n')
    buf.write('  }\n\n')
    buf.write("  print('${request.uri}');\n")
    buf.write('  switch (request.uri.toString()) {\n')
    for endpointName, endpointType in config_dict('endpoints').items():
        buf.write(f'    // {endpointType}\n')
        buf.write(f"    case '/{endpointName}': {{\n")
        if 'in' in endpointType or 'authLevel' in endpointType or endpointType.get('forwardToken', False):
            if 'in' in endpointType:
                buf.write(f'      final {endpointType.get("in", "void")} reqData;\n')
            if 'authLevel' in endpointType or endpointType.get('forwardToken', False):
                buf.write(f'      final {config["auth"]["out"]} token;\n')
            buf.write('      try {\n')
            # todo: if we can tell the difference between a utf8 decode error and a json typecast error we can
            # send back a bit more detail!
            buf.write(f'        final reqBody = jsonDecode(await utf8.decoder.bind(request).join());\n')
            if 'in' in endpointType:
                reqDataGetter = fromJson(endpointType['in'], "reqBody['data']")
                buf.write(f"        reqData = {reqDataGetter};\n")
            if 'authLevel' in endpointType or endpointType.get('forwardToken', False):
                buf.write(f"        token = reqBody['token'];\n")
            buf.write('      } catch (e, t) {\n')
            buf.write("        print('Object format error:\\n$e\\n$t');\n")
            buf.write("        request.response.write(jsonEncode({'code': APIException.values.indexOf(APIException.ObjectFormatError)}));\n")
            buf.write('        request.response.close();\n')
            buf.write('        return;\n')
            buf.write('      }\n\n')
        buf.write('      Map<String, dynamic> response;\n')
        buf.write('      try {\n')

        if 'authLevel' in endpointType:
            if endpointType['authLevel'] == 'Custom':
                buf.write(f'        if (!auth.{endpointName}Auth(token')
                if 'in' in endpointType:
                    buf.write(', reqData')
                buf.write(')) {\n')
            else:
                buf.write('        final tokenLevel = auth.validateToken(token);\n')
                buf.write(f'        if (AuthLevel.values.indexOf(tokenLevel) < AuthLevel.values.indexOf(AuthLevel.{endpointType["authLevel"]})) {{\n')
            buf.write("          request.response.write(jsonEncode({'code': APIException.values.indexOf(APIException.Unauthorized)}));\n")
            buf.write('          request.response.close();\n')
            buf.write('          return;\n')
            buf.write('        }\n\n')

        if 'out' in endpointType:
            buf.write("        response = {'data': ")
        
        if endpointName == '_authorize':
            responseGetter = f'auth.generateToken('
        elif endpointType.get('handledBy', 'main') == 'main':
            responseGetter = f'handler.{endpointName}('
        elif endpointType.get('handledBy', 'main') == 'auth':
            responseGetter = f'auth.{endpointName}('
        else:
            raise ValueError(f"Unknown request handler '{endpointType.get('handledBy', 'main')}'!")

        if 'out' not in endpointType:
            responseGetter = '        ' + responseGetter
        
        if endpointType.get('forwardToken', False):
            responseGetter += 'token'
            if 'in' in endpointType:
                responseGetter += ', '

        if 'in' in endpointType:
            responseGetter += 'reqData'
        
        responseGetter += ')'

        if 'out' in endpointType:
            buf.write(toJson(endpointType['out'], responseGetter))
            buf.write(", 'code': APIException.values.indexOf(APIException.Success)}")
        else:
            buf.write(responseGetter)
        
        buf.write(';\n')
        
        if 'out' not in endpointType:
            buf.write("        response = {'code': APIException.values.indexOf(APIException.Success)};\n")
        
        buf.write('      } on APIException catch (e, t) {\n')
        buf.write("        print('Handled APIException:\\n$e\\n$t');\n")
        buf.write("        response = {'code': APIException.values.indexOf(e)};\n")
        buf.write('      } catch (e, t) {\n')
        buf.write("        print('Unhandled exception from API:\\n$e\\n$t');\n")
        buf.write("        response = {'code': APIException.values.indexOf(APIException.InternalError)};\n")
        buf.write('      }\n')
        buf.write('      request.response.write(jsonEncode(response));\n')
        buf.write('      request.response.close();\n')
        buf.write('      break;\n')
        buf.write('    }\n')
    
    buf.write("    default: {\n")
    buf.write("      print('Unsupported endpoint!');\n")
    buf.write("      request.response.write(jsonEncode({'code': APIException.values.indexOf(APIException.UnsupportedEndpoint)}));\n")
    buf.write('      request.response.close();\n')
    buf.write('    }\n  }\n}\n')
    

def generate_frontend(buf: StringIO):
    buf.write('class API {\n')
    buf.write('  static void Function(APIException)? onError;\n\n')

    # can Dart not figure out it's guaranteed to not return?
    buf.write('  static Never _error(APIException error) {\n')
    buf.write('    onError?.call(error);\n')
    buf.write('    throw error;\n')
    buf.write('  }\n\n')

    if 'auth' in config:
        config['endpoints']['_authorize'] = config['auth']
        buf.write(f'  static {config["auth"]["out"]}? _token;\n')
        buf.write(f'  static Future<void> authorize({config["auth"]["in"]} credentials) async => _token = await _authorize(credentials);\n')
        buf.write('  static void clearToken() => _token = null;\n\n')

    for endpointName, endpointDetails in config_dict('endpoints').items():
        buf.write(f'  static Future<{endpointDetails.get("out", "void")}> {endpointName}(')
        if 'in' in endpointDetails:
            buf.write(f'{endpointDetails["in"]} request')
        buf.write(') async {\n')
        buf.write('    final Map<String, dynamic> res;\n')
        buf.write('    final int code;\n')
        buf.write('    try {\n')
        if USE_HTTPS:
            buf.write(f"      res = jsonDecode((await post(Uri.https('{API_URL}', '/{endpointName}')")
        else:
            buf.write(f"      res = jsonDecode((await post(Uri.http('{API_URL}', '/{endpointName}')")
        
        if 'in' in endpointDetails or 'authLevel' in endpointDetails or endpointDetails.get('forwardToken', False):
            buf.write(', body: jsonEncode({')
            if 'in' in endpointDetails:
                buf.write(f"'data': {toJson(endpointDetails['in'], 'request')}")
                if 'authLevel' in endpointDetails or endpointDetails.get('forwardToken', False):
                    buf.write(', ')
            if 'authLevel' in endpointDetails or endpointDetails.get('forwardToken', False):
                buf.write(f"'token': {toJson(config['auth']['out'], '_token!')}")
            buf.write("}), headers: {HttpHeaders.contentTypeHeader: 'application/json'}")
        buf.write(')).body);\n')
        buf.write("      code = res['code'] as int;\n")
        buf.write('    } catch (e) {\n')
        buf.write('      _error(APIException.InternalError);\n')
        buf.write('    }\n\n')
        buf.write('    if (APIException.values[code] != APIException.Success) { _error(APIException.values[code]); }\n')

        if 'out' in endpointDetails:
            buf.write('    try {\n')
            buf.write('      return ')
            buf.write(fromJson(endpointDetails["out"], "res['data']"))
            buf.write(';\n')
            buf.write('    } catch (e) {\n')
            buf.write('      _error(APIException.InternalError);\n')
            buf.write('    }\n')

        buf.write('  }\n\n')

    buf.write('}\n')

def generate(target: str, output_dir: str, config_dir: str):
    global config, API_URL, USE_HTTPS
    config = get_config(config_dir)
    API_URL = config['api_url']
    USE_HTTPS = config['use_https']

    buf = StringIO()
    buf.write("import 'dart:io';\nimport 'dart:convert';\n")
    if target == 'frontend':
        buf.write("import 'package:http/http.dart';\n")
    generate_base(buf)

    # can't use match cos we need to use python3.9 on the server due to a weird yaml bug in 3.10
    if target == 'server':
        generate_server(buf)
    elif target == 'frontend':
        generate_frontend(buf)
    elif target == 'thaum':
        generate_server(buf)
        generate_frontend(buf)
    else:
        raise ValueError('Unsupported target!')

    with open(f'{output_dir}/generated.dart', 'wt') as fh:
        fh.write(buf.getvalue())