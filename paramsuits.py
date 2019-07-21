#!/usr/bin/env python

import argparse
import sys
import boto3
import os
import binascii
import json

from botocore.exceptions import ClientError
from botocore.exceptions import NoRegionError

DEFAULT_REGION = "us-east-1"

class ArgumentFilter:
    '''
    Class to store filter related argument intput value
    '''
    def __init__(self, recursive = False, key_prefix = None, decrypt = False, tags = None, 
        show_path = False, encrypt = False, skip_tag = False, advanced_tier = False,
        list_type = False):
        self.recursive = recursive
        self.key_prefix = key_prefix
        self.decrypt = decrypt
        self.tags = tags
        self.show_path = show_path
        self.encrypt = encrypt
        self.skip_tag = skip_tag
        self.advanced_tier = advanced_tier
        self.list_type = list_type

class ParameterFilter:
    '''
    Class to match ParameterFilters definition used by boto3 ssm.describe_parameters 
    '''
    def __init__(self, key, option, values):
        self.Key = key
        self.Option = option
        self.Values = values

class NormedParamName:
    '''
    Class to store normalized parameter name
    '''
    def __init__(self, raw_name):
        self.raw_name = raw_name
        self.path = util_get_param_path(raw_name)
        self.name = util_get_param_name(raw_name)

def util_get_param_path(raw_name):
    '''
    Util method to extract paramter path from full name
    '''
    path = raw_name.rsplit('/', 1)[0]
    return (path if path != raw_name else '/')

def util_get_param_name(raw_name):
    '''
    Util method to extract paramter name from full name
    '''
    parts = raw_name.rsplit('/', 1)
    return (parts[0] if len(parts) == 1 else parts[1])

def util_normalize_path(path):
    '''
    Util method to normailize path
    '''
    if path and len(path) > 1:
        return path.rstrip('/')
    return '/'

def util_form_param_full_path(path, name):
    '''
    Util method to form param full path
    '''
    if path == '/':
        return name
    else:
        return path.rstrip('/') + '/' + name.lstrip('/')
 
def get_cli_parser():
    '''
    Global client input parser
    '''
    parsers = {}
    parsers['super'] = argparse.ArgumentParser(description = "Tool to manage parameters in AWS SSM parameter store")

    parsers['super'].add_argument('-r', '--region', 
        help = 'the AWS region in which the parameter store resides. '
            'If a region is not specified, the tool will use env variable AWS_DEFAULT_REGION '
            'if it\'s available. Otherwise it will try to use the value in `~/.aws/config`.'
            'As a last resort, it will use ' + DEFAULT_REGION
        )
    
    parsers['super'].add_argument('-p', '--path', default = '/',
        help = 'Parameter path in parameter store. Use root path if no value assigned')

    role_parser = parsers['super'].add_mutually_exclusive_group()
    role_parser.add_argument('-P', '--profile', default = None,
        help ='Boto config profile to use when connection to AWS')
    role_parser.add_argument('-A', '--arn', default = None, help = 'AWS IAM ARN for AssumeRole')

    subparsers = parsers['super'].add_subparsers(
        help = 'Try commands like "{name} get -h" or '
            '"{name} put --help" to get each sub command\'s '
            'options'.format(name = sys.argv[0])
    )

    # Action keys
    action = 'keys'
    parsers[action] = subparsers.add_parser(action, help = 'List all keys in the store which match given condtions')
    parsers[action].add_argument('-recursive', '--recursive', action = 'store_true', 
        help = 'Traverse through all child paths recursively'
    )
    parsers[action].add_argument('-showPath', '--show-path', dest = 'show_path', action = 'store_true',
        help = 'Display parameter name with path')
    parsers[action].add_argument('-prefix', '--prefix', default = None,
        help = 'Filter parameter name with given prefix, parameter path is not considered as prefix')

    parsers[action].set_defaults(action = action)

    # Action get
    action = 'get'
    parsers[action] = subparsers.add_parser(action, 
        help = 'Get parameter value of a given name.'
            'If more than one paramters found,'
            'only the first matched value will be retured'
    )
    parsers[action].add_argument('param', type = str,
        help = 'The name of the paramter to get.'
    )

    parsers[action].set_defaults(action = action)

    # Action getAll
    action = 'getAll'
    parsers[action] = subparsers.add_parser(action, 
        help ='List name and value for all parameters of a given path'
            'Each paramter will display one line as {{name}} = {{value}}'
    )
    parsers[action].add_argument('-decrypt', '--decrypt', action = 'store_true',
        help ='Decrypt value for SecureString type of parameter'
    )
    parsers[action].add_argument('-recursive', '--recursive', action = 'store_true', 
        help = 'Traverse through all child paths recursively'
    )
    parsers[action].add_argument('-showPath', '--show-path', dest = 'show_path', action = 'store_true',
        help = 'Display parameter name with path')

    parsers[action].set_defaults(action = action)

    # Action put
    action = 'put'
    parsers[action] = subparsers.add_parser(action,
        help = 'Put a parameter into parameter store. '
            'Policy is not supported in current version'
    )
    parsers[action].add_argument('param_name', type = str, help = 'Parameter name to put')
    parsers[action].add_argument('param_value', type = str, nargs = '+',    
        help = 'Parameter value to put. If the value is a list, devide each value by space')
    parsers[action].add_argument('-encrypt', '--encrypt', action = 'store_true', 
        help = 'If the parameter type is SecureString. Ignored for list type of values'
    )
    parsers[action].add_argument('-advancedTier', '--advanced-tier', dest = 'advanced_tier',
        action = 'store_true',
        help = 'Mark this parameter is Advanced tier parameter'
    )
    parsers[action].add_argument('-isList', '--is-list', dest = 'is_list', action = 'store_true',
        help = 'Parameter type is StringList. Only needed for single value list')
    parsers[action].add_argument('-keyId', '--key-id', dest = 'key_id', default = None,
        help = 'Key Id to encrypt parameter. Used when -encrypt option is used')
    tag_parser = parsers[action].add_mutually_exclusive_group()
    tag_parser.add_argument('-skipTagging', '--skip-tagging', dest = 'skip_tag', action = 'store_true',
        help = 'Not add any tags to this parameter'
    )
    tag_parser.add_argument('-tags', '--tags', type = json.loads, default = '{}',
        help = 'Tags for the parameter. Applies default tags of name and user '
            'if the neither values are given through this option nor '
            '--skip-tagging is set'
    )
    parsers[action].set_defaults(action = action)

    return parsers

def extract_argment_filter(args):
    '''
    Extract filter condition from input arguments
    '''
    recursive = args.recursive if hasattr(args, 'recursive')  else False
    key_prefix = args.prefix if hasattr(args, 'prefix') else None
    decrypt = args.decrypt if hasattr(args, 'decrypt') else False
    show_path = args.show_path if hasattr(args, 'show_path') else False
    tags = args.tags if hasattr(args, 'tags') else None
    encrypt = args.encrypt if hasattr(args, 'encrypt') else False
    skip_tag = args.skip_tag if hasattr(args, 'skip_tag') else False
    advanced_tier = args.advanced_tier if hasattr(args, 'advanced_tier') else False
    list_type = args.is_list if hasattr(args, 'is_list') else False

    argumentFilter = ArgumentFilter(recursive = recursive, key_prefix = key_prefix, decrypt = decrypt, 
        show_path = show_path, tags = tags, encrypt = encrypt, skip_tag = skip_tag,
        advanced_tier = advanced_tier, list_type = list_type)
    return argumentFilter

def get_assume_role_credentials(arn):
    sts_client = boto3.client('sts')
    # Use client object and pass the role ARN
    assumed_role_object = sts_client.assume_role(RoleArn = arn,
                                               RoleSessionName = "AssumeRolePropTweezersSession1")
    credentials = assumed_role_object['Credentials']
    return dict(aws_access_key_id = credentials['AccessKeyId'],
                aws_secret_access_key = credentials['SecretAccessKey'],
                aws_session_token = credentials['SessionToken'])

def get_session_params(profile, arn):
    params = {}
    if profile is None and arn:
        params = get_assume_role_credentials(arn)
    elif profile:
        params = dict(profileName = profile)
    
    return params

def get_session(aws_access_key_id = None, aws_secret_access_key = None,
                aws_session_token = None, profile_name = None):
    if get_session._cached_session is None:
        get_session._cached_session = boto3.Session(aws_access_key_id = aws_access_key_id,
                                                    aws_secret_access_key = aws_secret_access_key,
                                                    aws_session_token = aws_session_token,
                                                    profile_name = profile_name)
    return get_session._cached_session
get_session._cached_session = None

def query_parameter_list(region, path, **session_params):
    '''
    Do a full scan through parameter store,
    return description of every matched properties
    '''

    session = get_session(**session_params)
    client = session.client('ssm', region_name = region)
    result = client.describe_parameters()
    parameters = result.get('Parameters')
    next_token = result.get('NextToken') 

    while next_token is not None:
        result = client.describe_parameters(NextToken = next_token)
        next_token = result.get('NextToken')
        extra_params = result.get('Parameters')
        if extra_params:
            parameters.extend(extra_params)
    
    return parameters

def query_parameter_value(path, param, region, **session_params):
    '''
    Get parameter value in parameter store
    '''
    session = get_session(**session_params)
    param_path = util_form_param_full_path(path, param)
    client = session.client('ssm', region_name = region)
    try:
        result = client.get_parameter(Name=param_path, WithDecryption=True)
        return result.get('Parameter')
    except ClientError:
        return None

def query_parameters_by_path(path, recursive, region, **session_params):
    '''
    Get parameters by path
    '''
    session = get_session(**session_params)
    client = session.client('ssm', region_name = region)
    try:
        result = client.get_parameters_by_path(
            Path = path,
            Recursive = recursive,
            WithDecryption = True
        )
        params = result.get('Parameters')
        next_token = result.get('NextToken')
        while next_token is not None:
            result = client.get_parameters_by_path(
                Path = path,
                Recursive = recursive,
                WithDecryption = True,
                NextToken = next_token
            )
            next_batch = result.get('Parameters')
            next_token = result.get('NextToken')
            if next_batch:
                params.extend(next_batch)
        return params
    except ClientError:
        return None

def query_current_user(region, **session_params):
    '''
    Get current user information
    '''
    session = get_session(**session_params)
    client = session.client('sts', region)
    return client.get_caller_identity()

def update_parameter_value(region, param_name, param_value, param_type, key_id = None, is_advanced_tier = False, **session_params):
    '''
    upsert a parameter value in SSM store
    '''
    session = get_session(**session_params)
    client = session.client('ssm', region_name = region)
    try:
        method_args = {
            "Name": param_name,
            "Value": param_value,
            "Type": param_type,
            "Overwrite": True
        }

        if key_id:
            method_args.update({"KeyId": key_id})

        if is_advanced_tier:
            method_args.update({"Tier", "Advanced"})
            
        client.put_parameter(**method_args)
        return True
    except ClientError as e:
        print('Failed to upsert parameter ' + param_name + ':' + e.response.get('Error', 'Unknown'))
        return False

def update_parameter_tag(region, name, tags, **session_params):
    '''
    Update tags for a parameter
    '''
    session = get_session(**session_params)
    client = session.client('ssm', region_name = region)
    client.add_tags_to_resource(
        ResourceType = 'Parameter',
        ResourceId = name,
        Tags = tags
    )
    return

def make_prop_arg_filter(path, arg_filter):
    '''
    Make property names fitler by conditions defined in arguments
    '''
    target_path = util_normalize_path(path)
    def prop_key_filter(name_obj):
        # Recursive search
        if arg_filter.recursive:
            if not name_obj.path.startswith(target_path):
                return False
        else:
            if name_obj.path != target_path:
                return False

        # Search key prefix
        if arg_filter.key_prefix:
            if not name_obj.name.startswith(arg_filter.key_prefix):
                return False

        return True       
    return prop_key_filter

def list_parameter_names(region, args, **session_params):
    '''
    Print parameter names of given input
    '''
    path = args.path
    show_path = args.show_path
    prop_list = query_parameter_list(region = region, path = path, **session_params)
    if prop_list:
        arg_filter = extract_argment_filter(args)
        name_filter = make_prop_arg_filter(path, arg_filter)
        raw_names = [d.get('Name') for d in prop_list if 'Name' in d]
        normed_names = [NormedParamName(n) for n in raw_names]
        qualified_names = sorted(filter(name_filter, normed_names))
        for name_obj in qualified_names:
            if show_path:
                print(name_obj.raw_name)
            else:
                print(name_obj.name)
    else:
        return
    
def get_single_value(region, args, **session_params):
    '''
    Print value of a given parameter if found
    '''
    path = args.path
    param = args.param
    valueObj = query_parameter_value(path = path, param = param, region = region, **session_params)
    if valueObj:
        print(valueObj.get('Value'))
        return
    else:
        return

def print_param_values(params, arg_filter):
    for param in params:
        raw_name = param.get('Name')
        display_name = raw_name if arg_filter.show_path else util_get_param_name(raw_name)
        raw_value = param.get('Value')
        param_type = param.get('Type')
        display_value = raw_value 
        if param_type == 'SecureString' and not arg_filter.decrypt:
            display_value = '***** (CRC:' + str(binascii.crc32(raw_value)) + ')'
        print(display_name + ' = ' + display_value)
    return

def get_parameter_values(region, args, **session_params):
    '''
    Print name and value pair of all parameters under given path
    '''
    path = args.path
    arg_filter = extract_argment_filter(args)
    params = query_parameters_by_path(path = path, recursive = arg_filter.recursive, region = region, **session_params)
    print_param_values(params, arg_filter)
    return

def upsert_single_parameter(region, args, **session_params):
    '''
    Creat or update a signle parameter value
    '''
    # Preparing data
    arg_filter = extract_argment_filter(args)
    raw_name = args.param_name
    path = args.path
    param_name = util_form_param_full_path(path = path, name = raw_name)
    raw_values = args.param_value
    key_id = None

    if len(raw_values) == 1 and not arg_filter.list_type:
        param_value = raw_values[0]
        if arg_filter.encrypt:
            param_type = 'SecureString'
        else:
            param_type = 'String'
            key_id = args.key_id if hasattr(args, 'key_id') else None
    else:
        param_value = ','.join(raw_values)
        param_type = 'StringList'

    # update_parameter_value(region, param_name, param_value, param_type, key_id = None, is_advanced_tier = False, **session_params)
    result = update_parameter_value(region = region, param_name = param_name, param_value = param_value,
        key_id = key_id, param_type = param_type, is_advanced_tier = arg_filter.advanced_tier)
   
    # Update tags
    if not arg_filter.skip_tag and result:
        tags_dict = arg_filter.tags
        if not tags_dict:
            tags_dict = {}
            current_user = query_current_user(region, **session_params)
            arn_parts= current_user.get('Arn').rsplit('/', 1)
            if len(arn_parts) == 2:
                tags_dict.update({"User": arn_parts[1]})
            tags_dict.update({"Name": raw_name})
        tags = [{"Key": key, "Value": value} for key, value in tags_dict.items()]
        update_parameter_tag(region = region, name = param_name, tags = tags, **session_params)
    return

def main():
    parsers = get_cli_parser()
    args = parsers['super'].parse_args()

    # Check for assume role and set  session params
    session_params = get_session_params(args.profile, args.arn)

    try:
        region = args.region
        session = get_session(**session_params)
        session.client('ssm', region_name = region)
    except NoRegionError:
        if 'AWS_DEFAULT_REGION' not in os.environ:
            region = DEFAULT_REGION

    if 'action' in vars(args):
        if args.action == 'keys':
            list_parameter_names(region, args, **session_params)
            return
        elif args.action == 'get':
            get_single_value(region, args, **session_params)
            return
        elif args.action == 'getAll':
            get_parameter_values(region, args, **session_params)
            return
        elif args.action == 'put':
            upsert_single_parameter(region, args, **session_params)
            return
    else:
        parsers['super'].print_help()

if __name__ == '__main__':
    main()