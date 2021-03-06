#!/usr/bin/env python3
import sys
import xmlrpc.client

from common import get_env, mgm_uri

def main():
    env = get_env()

    with xmlrpc.client.ServerProxy(mgm_uri(env)) as client:
        client.disconnect_user(env['NAUM_CHAL'], env['COMMON_NAME'], env['TRUSTED_IP'], int(env['TRUSTED_PORT']))

if __name__ == '__main__':
    main()
