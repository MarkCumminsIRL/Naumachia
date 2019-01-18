#!/usr/bin/env python3
import sys
import xmlrpc.client

from common import get_env, mgm_uri

OVPN_DYN_TEMPLATE = """
vlan-pvid {vlan:d}
"""

def main():
    env = get_env()

    with xmlrpc.client.ServerProxy(mgm_uri(env)) as client:
        vlan = client.connect_user(env['NAUM_CHAL'], env['COMMON_NAME'], env['TRUSTED_IP'], int(env['TRUSTED_PORT']))

    with open(sys.argv[1], 'w') as ovpn_dyn:
        ovpn_dyn.write(OVPN_DYN_TEMPLATE.format(vlan=vlan))

if __name__ == '__main__':
    main()
