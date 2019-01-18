import os

import yaml

ENVFILE = '/env.yaml'

def get_env():
    env = {}
    y_env = {}
    with open(ENVFILE) as f:
        y_env = yaml.safe_load(f)

    env['HOSTNAME'] = y_env.get('hostname')
    env['NAUM_MGM_HOST'] = y_env.get('naum_mgm_host')
    env['NAUM_VETHHOST'] = y_env.get('naum_vethhost')
    env['NAUM_FILES'] = y_env.get('naum_files')
    env['NAUM_CHAL'] = y_env.get('naum_chal')

    env['COMMON_NAME'] = os.getenv('common_name')
    env['TRUSTED_IP'] = os.getenv('trusted_ip')
    env['TRUSTED_PORT'] = os.getenv('trusted_port')

    return env

def mgm_uri(env):
    return 'http://{}:{}'.format(env['NAUM_MGM_HOST'], 8000)
