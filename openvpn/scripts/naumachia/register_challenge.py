#!/usr/bin/env python3
import sys
import xmlrpc.client

from common import get_env, mgm_uri

def main():
    env = get_env()

    with xmlrpc.client.ServerProxy(mgm_uri(env)) as client:
        client.register_challenge(env['NAUM_CHAL'], env['NAUM_VETHHOST'], env['NAUM_FILES'])

if __name__ == '__main__':
    main()
