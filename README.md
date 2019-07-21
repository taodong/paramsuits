# paramsuits
A Python tool to manage parameters in AWS SSM parameter store

## Dependencies
1. AWS client configured
2. boto3 version 1.4.6 or later installed

## Installation
```
pip install paramsuits
```

## Usage
```
usage: paramsuits [-h] [-r REGION] [-p PATH] [-P PROFILE | -A ARN] {keys,get,getAll,put} ...

Tool to manage parameters in AWS SSM parameter store

get
    usage: paramsuits.py get [-h] param

    Get parameter value of a given name.If more than one paramters found, only the first matched value will be retured

    positional arguments:
        param       The name of the paramter to get

getAll
    usage: paramsuits.py getAll [-h] [-decrypt] [-recursive] [-showPath]

    List name and value for all parameters of a given pathEach paramter will display one line as {{name}} = {{value}}

    optional arguments:
        -decrypt, --decrypt         Decrypt value for SecureString type of parameter
        -recursive, --recursive     Traverse through all child paths recursively
        -showPath, --show-path      Display parameter name with path

keys
    usage: paramsuits.py keys [-h] [-recursive] [-showPath] [-prefix PREFIX]

    List all keys in the store which match given condtions

    optional arguments:
        -recursive, --recursive     Traverse through all child paths recursively
        -showPath, --show-path      Display parameter name with path
        -prefix PREFIX, --prefix PREFIX     Filter parameter name with given prefix, parameter path is not considered as prefix

put
    usage: paramsuits.py put [-h] [-encrypt] [-advancedTier] [-isList] [-keyId KEY_ID] [-skipTagging | -tags TAGS param_name param_value [param_value ...]

    Put a parameter into parameter store. Policy is not supported in current version

    positional arguments:
        param_name            Parameter name to put
        param_value           Parameter value to put. If the value is a list, devide each value by space

    optional arguments:
        -encrypt, --encrypt   If the parameter type is SecureString. Ignored for list type of values
        -advancedTier, --advanced-tier      Mark this parameter is Advanced tier parameter
        -isList, --is-list                  Parameter type is StringList. Only needed for single value list
        -keyId KEY_ID, --key-id KEY_ID      Key Id to encrypt parameter. Used when -encrypt option is used
        -skipTagging, --skip-tagging        Not add any tags to this parameter
        -tags TAGS, --tags TAGS             Tags for the parameter. Applies default tags of name and user if the neither values are given through this option nor --skip-tagging is set

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        the AWS region in which the parameter store resides.
                        If a region is not specified, the tool will use env
                        variable AWS_DEFAULT_REGION if it's available.
                        Otherwise it will try to use the value in
                        `~/.aws/config`.As a last resort, it will use us-
                        east-1
  -p PATH, --path PATH  Parameter path in parameter store. Use root path if no
                        value assigned
  -P PROFILE, --profile PROFILE
                        Boto config profile to use when connection to AWS
  -A ARN, --arn ARN     AWS IAM ARN for AssumeRole
```


