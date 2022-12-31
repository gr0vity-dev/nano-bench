def get_error_messages(key, *args):
    error_messages = {
        "rpc_url_not_found": "'rpc_url' must be defined in your config file",
        "command_failed": "[{}] failed with status: [{}]",
        "undefined_shell_var": "Undefined mandatory shell_var [{}]",
        "invalid_env": "env must be in ['nanolocal', 'test','beta','live']",
        "missing_build_block": "No building_block [{}] defined in [{}]",
        "misconfig": "Misconfiguration detected! [{}] not allowed for [{}]",
        "eof": "unexpected EOF"
    }

    if key not in error_messages:
        error_messages[key] = f"You tried to raise an undefined error {key}"

    return error_messages[key].format(*args[0])


def raise_exception(error_key, *args):
    error_message = get_error_messages(error_key, args)

    raise Exception(error_message.strip())


def raise_value_error(error_key, *args):
    error_message = get_error_messages(error_key, args)
    raise ValueError(error_message.strip())
